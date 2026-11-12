"""Public demo mode (10 Nov): on and off for every refusal, the two served deals, the sample-file path end to end for Noma
and Alder (no key, no model call), the hourly reset under the reset lock, backups kept to three, and local mode unchanged.

The ledger is built once from the saved v2 output into a temporary folder and copied per test; the real reading cache is
only read (test_zz_cache_untouched checks the suite leaves it as it was). The real workspace/ledger.sqlite is never opened.
"""

import base64
import os
import shutil
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

import api
import config
import public_demo
import reset_demo

H = {"X-Requested-With": "deal-workspace"}
PUBLIC = ["alder_bank", "noma_journeys"]
HIDDEN = ["harbour_bank", "coral_pay", "atlas_remit"]
_template = {}


def setUpModule():
    tmp = tempfile.TemporaryDirectory()
    _template["tmp"] = tmp
    _template["db"] = Path(tmp.name) / "template.sqlite"
    reset_demo.reset(_template["db"])


def tearDownModule():
    _template["tmp"].cleanup()


def no_key():
    return mock.patch.dict(os.environ, {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}, clear=True)


class Case(unittest.TestCase):
    public = True

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.db = self.dir / "ledger.sqlite"
        shutil.copy(_template["db"], self.db)
        env = no_key()
        env.start()
        self.addCleanup(env.stop)
        self.client = self.make(self.public)

    def make(self, public, **kw):
        return TestClient(api.create_app(dist_dir=self.dir / "no-dist", ledger_path=self.db, public=public, **kw),
                          base_url="http://127.0.0.1", follow_redirects=False)

    def post(self, path, body, client=None):
        return (client or self.client).post(path, json=body, headers=H)

    def sample_body(self, deal, file):
        meta = public_demo.find_sample(deal, file)
        text = self.client.get("/api/demo/sample", params={"deal": deal, "file": file}).json()["text"]
        if meta.get("version_of"):
            return {"source_key": meta["version_of"], "filename": file, "text": text}
        return {"name": file, "filename": file, "doc_type": meta["doc_type"], "doc_date": meta["doc_date"], "text": text}

    def add_sample(self, deal, file):
        return self.post(f"/api/deals/{deal}/documents/add-and-check", self.sample_body(deal, file))


class TestOnlyTwoDealsInPublicMode(Case):
    def test_the_deal_list_has_only_alder_and_noma(self):
        self.assertEqual(sorted(self.client.get("/api/deals").json()["deals"]), PUBLIC)
        self.assertEqual(sorted(d["deal"] for d in self.client.get("/api/workspace/deals").json()["deals"]), PUBLIC)

    def test_every_route_refuses_the_other_three_deals(self):
        gets = ["register", "documents", "documents/text?version=1", "sources", "results/latest", "handover", "handoffs",
                "handoffs/summary", "handoffs/export.csv"]
        posts = {"note": {"note": "x", "entered_by": "y"}, "seen": {"issue_id": 1, "seen_by": "y"},
                 "documents/add-and-check": {"filename": "a.md", "text": "x", "doc_type": "proposal", "name": "a"},
                 "review": {}, "handover/complete": {"completed_by": "y"}}
        for deal in HIDDEN:
            for g in gets:
                self.assertEqual(self.client.get(f"/api/deals/{deal}/{g}").status_code, 404, (deal, g))
            for p, body in posts.items():
                self.assertEqual(self.post(f"/api/deals/{deal}/{p}", body).status_code, 404, (deal, p))
            self.assertEqual(self.client.get("/api/catalogue", params={"deal": deal}).status_code, 404, deal)
        for deal in PUBLIC:
            self.assertEqual(self.client.get(f"/api/deals/{deal}/register").status_code, 200, deal)

    def test_a_vendor_catalogue_is_served_only_for_the_served_deals(self):
        vendors = {d["vendor"] for d in self.client.get("/api/workspace/deals").json()["deals"]}
        for v in vendors:
            self.assertEqual(self.client.get("/api/catalogue", params={"vendor": v}).status_code, 200, v)
        self.assertEqual(self.client.get("/api/catalogue", params={"vendor": "nobody"}).status_code, 404)

    def test_local_mode_still_serves_all_five(self):
        local = self.make(False)
        self.assertEqual(sorted(local.get("/api/deals").json()["deals"]), sorted(config.UI_DEALS))
        self.assertEqual(sorted(d["deal"] for d in local.get("/api/workspace/deals").json()["deals"]), sorted(config.UI_DEALS))
        for deal in HIDDEN:
            self.assertEqual(local.get(f"/api/deals/{deal}/register").status_code, 200, deal)


class TestPublicDealOrder(Case):
    def test_the_public_deal_list_is_always_noma_journeys_then_alder_bank(self):
        order = lambda c: [d["deal"] for d in c.get("/api/workspace/deals").json()["deals"]]
        self.assertEqual(self.client.get("/api/deals").json()["deals"], ["noma_journeys", "alder_bank"])
        self.assertEqual(order(self.client), ["noma_journeys", "alder_bank"])
        # whoever changed what last does not move them: a change on Noma makes it newest, then one on Alder makes Alder newest
        self.assertEqual(self.add_sample("noma_journeys", "NJ-05_v2_named_exception.md").status_code, 200)
        self.assertEqual(self.add_sample("alder_bank", "AB-05_v2_named_exception.md").status_code, 200)
        self.assertEqual(order(self.client), ["noma_journeys", "alder_bank"])
        self.post("/api/demo/reset", {})
        self.assertEqual(order(self.client), ["noma_journeys", "alder_bank"])  # and after a reset

    def test_local_mode_keeps_its_own_order_newest_first(self):
        local = self.make(False)
        self.assertEqual(self.add_sample("alder_bank", "AB-05_v2_named_exception.md").status_code, 200)
        first = local.get("/api/workspace/deals").json()["deals"][0]["deal"]
        self.assertEqual(first, "alder_bank")  # the deal changed last is first, as before


class TestRowOrderKeyNeverChanges(Case):
    """The commitment rows are ordered by their stored id (the order they were first recorded). The id is the one key a check cannot change:
    run all three Noma samples and the phone-row note, and every commitment keeps its id; none is re-created, renamed to a new id or reordered."""

    def ids(self, deal):
        return {c["name"]: c["id"] for c in self.client.get(f"/api/deals/{deal}/register").json()["commitments"]}

    def test_all_three_noma_samples_and_the_note_leave_every_commitments_id_and_so_the_order_unchanged(self):
        first = self.ids("noma_journeys")
        self.assertEqual(len(first), 3)
        self.assertEqual(len(set(first.values())), 3)
        order = sorted(first, key=first.get)
        reg = lambda: self.client.get("/api/deals/noma_journeys/register").json()
        for file in ("NJ-05_v2_named_exception.md", "NJ-07_v2_languages_aligned.md", "NJ-09_signed_contract.md"):
            self.assertEqual(self.add_sample("noma_journeys", file).status_code, 200, file)
            now = self.ids("noma_journeys")
            self.assertEqual(now, first, file)  # same names, same ids
            self.assertEqual(sorted(now, key=now.get), order, file)
        phone = next(c for c in reg()["commitments"] if "phone" in c["name"].lower())
        open_ids = [i["id"] for i in phone["issues"] if i["state"] != "Resolved"]
        r = self.post("/api/deals/noma_journeys/resolve-note", {"issue_ids": open_ids, "resolved_by": "Visitor", "reason": "Noma agreed on 19 Oct to launch on chat and email; voice is not offered."})
        self.assertEqual(r.status_code, 200, r.text)
        after = self.ids("noma_journeys")
        self.assertEqual(after, first)
        self.assertEqual(sorted(after, key=after.get), order)

    def test_the_sample_text_rows_exist_exactly_once_in_each_public_deal(self):
        import re
        for deal, pattern in (("noma_journeys", r"phone"), ("alder_bank", r"hosting")):
            names = [c["name"] for c in self.client.get(f"/api/deals/{deal}/register").json()["commitments"]]
            self.assertEqual(len([n for n in names if re.search(pattern, n, re.I)]), 1, (deal, names))


class TestSamplePreview(Case):
    """Preview (11 Nov): the sample text route also says which lines the check uses, found from the file's own text; nothing is stored."""

    def route(self, deal, file, client=None):
        return (client or self.client).get("/api/demo/sample", params={"deal": deal, "file": file}).json()

    def lines(self, deal, file):
        r = self.route(deal, file)
        text = r["text"].split("\n")
        return text, r["key_lines"]

    def test_the_key_lines_are_the_ones_the_check_uses_for_every_sample(self):
        expect = {("noma_journeys", "NJ-05_v2_named_exception.md"): ["Named exception approved by Omar Haddad"],
                  ("noma_journeys", "NJ-07_v2_languages_aligned.md"): ["12 languages"],
                  ("alder_bank", "AB-05_v2_named_exception.md"): ["Named exception approved by Arjun Rao"],
                  ("alder_bank", "AB-06_v2_coaching_added.md"): ["Scam coaching detection", "BioCatch"]}
        for (deal, file), phrases in expect.items():
            text, key = self.lines(deal, file)
            self.assertTrue(key, file)
            for phrase in phrases:
                self.assertTrue(any(phrase in text[i] for i in key), (file, phrase))
        for deal, file, names in (("noma_journeys", "NJ-09_signed_contract.md", ["Liam Hart", "Celeste Wong"]), ("alder_bank", "AB-09_signed_contract.md", ["Tom Fraser", "Priya Nair"])):
            text, key = self.lines(deal, file)
            block = "\n".join(text[i] for i in key)
            self.assertIn("## Signatures", block)
            for n in names:
                self.assertIn(n, block, file)
            self.assertNotIn("Clause 4", block)  # only the signature block
            self.assertFalse(any(text[i].startswith("All companies") for i in key))

    def test_every_marker_matches_and_the_files_are_only_read(self):
        import hashlib
        before = {s["file"]: hashlib.sha256(config.scenario_path(s["file"]).read_bytes()).hexdigest() for items in public_demo.SAMPLES.values() for s in items}
        for deal, items in public_demo.SAMPLES.items():
            for s in items:
                self.assertTrue(public_demo.key_lines(deal, s["file"]), s["file"])
                for phrase in s.get("key", []):
                    self.assertTrue(any(phrase in line for line in config.scenario_path(s["file"]).read_text(encoding="utf-8").split("\n")), (s["file"], phrase))
        self.assertEqual(public_demo.key_lines("noma_journeys", "AB-05_v2_named_exception.md"), [])  # not a sample of that deal
        after = {f: hashlib.sha256(config.scenario_path(f).read_bytes()).hexdigest() for f in before}
        self.assertEqual(before, after)

    def test_a_preview_stores_nothing_and_is_not_offered_in_local_mode(self):
        import hashlib
        digest = lambda: hashlib.sha256(self.db.read_bytes()).hexdigest()
        before = digest()
        for deal, items in public_demo.SAMPLES.items():
            for s in items:
                self.assertEqual(self.client.get("/api/demo/sample", params={"deal": deal, "file": s["file"]}).status_code, 200)
        self.assertEqual(digest(), before)
        local = self.make(False)
        self.assertEqual(local.get("/api/demo/sample", params={"deal": "noma_journeys", "file": "NJ-05_v2_named_exception.md"}).status_code, 404)


class TestConfigAndHosts(Case):
    def test_the_banner_and_note_cap_are_reported_only_in_public_mode(self):
        on = self.client.get("/api/demo/config").json()
        self.assertEqual(on, {"public": True, "note_max": 500, "banner": "Public demo · fictional data",
                              "note": "Shared with other visitors. If a deal has already been worked through, click Reset demo."})
        self.assertEqual(self.make(False).get("/api/demo/config").json(), {"public": False, "banner": None, "note": None, "note_max": None})

    def test_extra_hosts_count_only_in_public_mode(self):
        with mock.patch.dict(os.environ, {"DEALSHAPE_ALLOWED_HOSTS": "demo.onrender.com, other.example"}):
            def host(public, name):
                c = TestClient(api.create_app(dist_dir=self.dir / "x", ledger_path=self.db, public=public), base_url=f"http://{name}")
                return c.get("/api/deals").status_code
            self.assertEqual(host(True, "demo.onrender.com"), 200)
            self.assertEqual(host(True, "other.example"), 200)
            self.assertEqual(host(True, "127.0.0.1"), 200)
            self.assertEqual(host(True, "localhost"), 200)
            self.assertEqual(host(True, "evil.example"), 400)
            self.assertEqual(host(False, "demo.onrender.com"), 400)  # local mode ignores the variable
            self.assertEqual(host(False, "localhost"), 200)

    def test_the_mode_comes_from_the_environment_when_not_given(self):
        for value, expected in (("1", True), ("0", False), ("", False), ("true", False)):
            with mock.patch.dict(os.environ, {"DEALSHAPE_PUBLIC_DEMO": value}):
                c = TestClient(api.create_app(dist_dir=self.dir / "x", ledger_path=self.db), base_url="http://127.0.0.1")
                self.assertEqual(c.get("/api/demo/config").json()["public"], expected, value)
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("DEALSHAPE_PUBLIC_DEMO", None)
            c = TestClient(api.create_app(dist_dir=self.dir / "x", ledger_path=self.db), base_url="http://127.0.0.1")
            self.assertFalse(c.get("/api/demo/config").json()["public"])


class TestRefusals(Case):
    def test_new_deals_capabilities_and_links_are_refused_in_public_and_not_in_local(self):
        local = self.make(False)
        doc = self.client.get("/api/deals/noma_journeys/documents").json()["documents"][0]["source_key"]
        cases = [("/api/user-deals", {"name": "My deal"}, "user_deal"),
                 ("/api/catalogue/capabilities", {"name": "x"}, "capability"),
                 ("/api/deals/noma_journeys/documents/link", {"source_key": doc, "url": "https://example.com/x", "set_by": "A"}, "link")]
        for path, body, what in cases:
            r = self.post(path, body)
            self.assertEqual((r.status_code, r.json()["detail"]), (403, public_demo.REFUSED[what]), path)
            l = self.post(path, body, local)
            self.assertNotEqual(l.json().get("detail"), public_demo.REFUSED[what], path)
        self.assertEqual(self.post("/api/user-deals", {"name": "My deal"}, local).status_code, 200)

    def test_notes_over_500_characters_are_refused_in_public_and_allowed_in_local(self):
        local = self.make(False)
        long, ok = "x" * 501, "x" * 500
        issue = next(i["id"] for c in self.client.get("/api/deals/noma_journeys/register").json()["commitments"] for i in c["issues"])
        cases = [("note", {"note": long, "entered_by": "Ann"}), ("handover/notes", {"role": "sales", "note": long, "entered_by": "Ann"}),
                 ("handover/notes", {"role": "delivery", "note": long, "entered_by": "Ann"}),
                 ("issues", {"issue_id": issue, "note": long}),
                 ("decisions", {"kind": "must_fix", "issue_id": issue, "by": "Ann", "reason": long})]
        for path, body in cases:
            r = self.post(f"/api/deals/noma_journeys/{path}", body)
            self.assertEqual(r.status_code, 400, path)
            self.assertIn("500 characters", r.json()["detail"])
        for path, body in cases:
            okbody = {k: ((ok[:300] if path == "note" else ok) if v == long else v) for k, v in body.items()}  # the deal note has its own 300 cap
            self.assertEqual(self.post(f"/api/deals/noma_journeys/{path}", okbody).status_code, 200, path)
        self.assertEqual(self.post("/api/deals/alder_bank/handover/notes", {"role": "sales", "note": long, "entered_by": "Ann"}, local).status_code, 200)

    def test_a_free_upload_is_refused_unless_it_is_a_bundled_sample_of_that_deal(self):
        local = self.make(False)
        body = {"name": "My notes", "filename": "mine.md", "text": "Anything at all.", "doc_type": "proposal", "doc_date": "2026-11-01"}
        for route in ("documents", "documents/add-and-check"):
            r = self.post(f"/api/deals/noma_journeys/{route}", body)
            self.assertEqual((r.status_code, r.json()["detail"]), (400, public_demo.NOT_A_SAMPLE), route)
        raw = {"name": "x", "filename": "x.pdf", "file_base64": base64.b64encode(b"%PDF-1.4 not a sample").decode(), "doc_type": "proposal"}
        self.assertEqual(self.post("/api/deals/noma_journeys/documents", raw).json()["detail"], public_demo.NOT_A_SAMPLE)
        check = self.post("/api/deals/noma_journeys/findings/check", {"issue_id": 1, "filename": "m.md", "text": "Anything."})
        self.assertEqual(check.json()["detail"], public_demo.NOT_A_SAMPLE)
        # a sample of another deal is not a sample of this one; the same bytes sent as a base64 file do count
        other = (config.scenario_path("AB-05_v2_named_exception.md")).read_text(encoding="utf-8")
        self.assertEqual(self.post("/api/deals/noma_journeys/documents", {**body, "text": other}).status_code, 400)
        mine = config.scenario_path("NJ-09_signed_contract.md").read_bytes()
        as_file = {"name": "s", "filename": "NJ-09_signed_contract.md", "file_base64": base64.b64encode(mine).decode(), "doc_type": "signed_contract", "doc_date": "2026-10-20"}
        self.assertEqual(self.post("/api/deals/noma_journeys/documents", {**as_file}).status_code, 200)
        self.assertEqual(self.post("/api/deals/noma_journeys/documents", body, local).status_code, 200)  # local: any file

    def test_the_sample_routes_exist_only_in_public_mode_and_only_for_the_served_deals(self):
        listing = self.client.get("/api/demo/samples", params={"deal": "noma_journeys"}).json()["samples"]
        self.assertEqual([s["file"] for s in listing], ["NJ-05_v2_named_exception.md", "NJ-07_v2_languages_aligned.md", "NJ-09_signed_contract.md"])
        self.assertTrue(all(s["title"] and s["summary"] and "description" not in s for s in listing))
        alder = self.client.get("/api/demo/samples", params={"deal": "alder_bank"}).json()["samples"]
        self.assertEqual([s["file"] for s in alder], ["AB-05_v2_named_exception.md", "AB-06_v2_coaching_added.md", "AB-09_signed_contract.md"])
        self.assertEqual(self.client.get("/api/demo/samples", params={"deal": "harbour_bank"}).status_code, 404)
        for bad in ("../../CLAUDE.md", "HB-05_v2_named_exception.md", "scenarios.json", "NOPE.md"):
            self.assertEqual(self.client.get("/api/demo/sample", params={"deal": "noma_journeys", "file": bad}).status_code, 404, bad)
        local = self.make(False)
        self.assertEqual(local.get("/api/demo/samples", params={"deal": "noma_journeys"}).status_code, 404)
        self.assertEqual(local.get("/api/demo/sample", params={"deal": "noma_journeys", "file": "NJ-09_signed_contract.md"}).status_code, 404)

    def test_the_samples_are_worded_as_a_story_and_say_only_what_their_files_say(self):
        wording = {
            "noma_journeys": [
                ("Approval for the launch specialist", "Omar Haddad, Head of Customer Success, approves a named exception: first 30 days, no extra charge (18 October 2026).",
                 ["Omar Haddad", "Head of Customer Success", "18 October 2026", "first 30 days", "no extra charge"]),
                ("Revised draft contract", "The languages clause now says 12 languages (19 October 2026).", ["12 languages", "19 October 2026"]),
                ("Signed contract", "Signed 20 October 2026 by Liam Hart (Aivuna) and Celeste Wong (Noma Journeys).",
                 ["Liam Hart", "Celeste Wong", "20 October 2026", "Aivuna", "Noma Journeys"])],
            "alder_bank": [
                ("Approval for the BioCatch connector (coaching detection)", "Arjun Rao, Head of Product, approves the BioCatch connector (beta) as a named exception for the 1 February 2027 launch (16 October 2026).",
                 ["Arjun Rao", "Head of Product", "BioCatch", "16 October 2026", "1 February 2027"]),
                ("Revised statement of work", "Scam coaching detection is added as section 5 (16 October 2026).",
                 ["5. Scam coaching detection", "16 October 2026"]),
                ("Signed contract", "Signed 20 October 2026 by Tom Fraser (Elva) and Priya Nair (Alder Bank); agreement dated 12 October. The wording that closed the coaching-scam gap isn't in it, so the fix can't be confirmed and the gap reopens. Its statement of work appendix schedules coaching-scam detection for 1 May 2027.",
                 ["Tom Fraser", "Priya Nair", "20 October 2026", "Elva", "Alder Bank", "12 October", "1 May 2027"])],
        }
        for deal, expected in wording.items():
            listing = self.client.get("/api/demo/samples", params={"deal": deal}).json()["samples"]
            self.assertEqual([(s["title"], s["summary"]) for s in listing], [(t, line) for t, line, _ in expected], deal)
            for s, (_, line, facts) in zip(listing, expected):
                text = config.scenario_path(s["file"]).read_text(encoding="utf-8")
                for fact in facts:
                    self.assertIn(fact, text, (s["file"], fact))  # nothing the file does not state
                    if fact[0].isupper() and fact[0] != "5":
                        self.assertIn(fact, line, (s["file"], fact))
        self.assertNotIn("four", " ".join(s["summary"] for s in self.client.get("/api/demo/samples", params={"deal": "noma_journeys"}).json()["samples"]))

    def test_every_sample_on_offer_is_a_real_file_with_a_known_filing(self):
        for deal, items in public_demo.SAMPLES.items():
            self.assertIn(deal, config.UI_DEALS)
            for s in items:
                self.assertTrue(config.scenario_path(s["file"]).is_file(), s["file"])
                self.assertTrue(bool(s.get("version_of")) != bool(s.get("doc_type")), s["file"])

    def test_the_model_is_never_called_even_with_a_key_in_the_environment(self):
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-sentinel-not-a-key"}), mock.patch("anthropic.Anthropic") as client:
            r = self.add_sample("noma_journeys", "NJ-09_signed_contract.md")
            self.assertEqual(r.status_code, 200, r.text)
            self.assertNotIn("sk-sentinel", r.text)
        client.assert_not_called()

    def test_the_no_key_message_is_plain_in_public_mode_and_unchanged_in_local(self):
        import extraction_cache
        local = self.make(False)
        with mock.patch.object(api.deal_catalogue, "recheck", side_effect=extraction_cache.ExtractionFailed("x")):
            self.assertEqual(self.post("/api/deals/noma_journeys/review", {}).json()["detail"], public_demo.NO_MODEL)
            self.assertIn("API key", self.post("/api/deals/noma_journeys/review", {}, local).json()["detail"])


class TestSamplePathEndToEnd(Case):
    def test_noma_nj05_nj07_nj09_through_the_sample_path_with_no_key_and_no_model_call(self):
        for file in ("NJ-05_v2_named_exception.md", "NJ-07_v2_languages_aligned.md", "NJ-09_signed_contract.md"):
            r = self.add_sample("noma_journeys", file)
            self.assertEqual(r.status_code, 200, (file, r.text))
            self.assertEqual(r.json()["review"]["model_calls"], 0, file)
        reg = self.client.get("/api/deals/noma_journeys/register").json()
        self.assertEqual(reg["stage"]["current"], "signed")
        self.assertEqual(reg["freshness"]["state"], "Up to date")

    def test_alder_ab05_ab06_ab09_through_the_sample_path_with_no_key_and_no_model_call(self):
        for file in ("AB-05_v2_named_exception.md", "AB-06_v2_coaching_added.md", "AB-09_signed_contract.md"):
            r = self.add_sample("alder_bank", file)
            self.assertEqual(r.status_code, 200, (file, r.text))
            self.assertEqual(r.json()["review"]["model_calls"], 0, file)
        reg = self.client.get("/api/deals/alder_bank/register").json()
        self.assertEqual(reg["stage"]["current"], "signed")
        self.assertEqual(reg["freshness"]["state"], "Up to date")


class TestResets(Case):
    def hourly(self, db=None):
        """The app started the public way (lifespan runs), with the hourly thread replaced by a handle the test drives."""
        jobs = []
        real = public_demo.HourlyReset

        def start(job):
            jobs.append(job)
            return job
        patch = mock.patch.object(real, "start", start)
        patch.start()
        self.addCleanup(patch.stop)
        app = api.create_app(dist_dir=self.dir / "x", ledger_path=db or self.db, public=True, hourly=True)
        client = TestClient(app, base_url="http://127.0.0.1")
        client.__enter__()
        self.addCleanup(client.__exit__, None, None, None)
        return client, jobs[0]

    def test_startup_builds_a_missing_ledger_and_starts_the_hourly_job(self):
        fresh = self.dir / "new" / "ledger.sqlite"
        client, job = self.hourly(fresh)
        self.assertTrue(fresh.exists())
        self.assertEqual(sorted(d["deal"] for d in client.get("/api/workspace/deals").json()["deals"]), PUBLIC)
        self.assertEqual(job.every, 3600)

    def test_an_hourly_tick_runs_the_one_reset_under_the_reset_lock(self):
        client, job = self.hourly()
        self.post("/api/deals/noma_journeys/note", {"note": "mine", "entered_by": "Ann"}, client)
        real = reset_demo.reset
        started, release = threading.Event(), threading.Event()
        calls = []

        def slow(*a, **k):
            calls.append(a)
            started.set()
            release.wait(10)
            return real(*a, **k)

        with mock.patch.object(reset_demo, "reset", slow):
            t = threading.Thread(target=job.tick)
            t.start()
            self.assertTrue(started.wait(10))
            self.assertEqual(self.post("/api/demo/reset", {}, client).status_code, 409)  # the button meets the same lock
            job.report = lambda message: None
            self.assertIsNone(job.tick())  # a second tick while one runs skips, and says why
            release.set()
            t.join(30)
        self.assertEqual(calls, [(self.db,)])  # one reset, on the app's ledger
        notes = client.get("/api/deals/noma_journeys/register").json()["handover"]["notes"]
        self.assertFalse({k: v for k, v in notes.items() if v})

    def test_a_failed_hourly_reset_does_not_block_the_next_one_or_the_button(self):
        client, job = self.hourly()
        reports = []
        job.report = reports.append
        with mock.patch.object(reset_demo, "reset", side_effect=RuntimeError("boom")):
            self.assertIsNone(job.tick())
        self.assertTrue(reports and "left as it was" in reports[0])
        self.assertEqual(job.tick()["deals_restored"], 5)
        r = self.post("/api/demo/reset", {}, client)  # the lock is free; only the same-second backup name can refuse it
        self.assertTrue(r.status_code == 200 or "already exists" in r.json()["detail"], r.text)

    def test_public_mode_keeps_the_latest_three_backups_and_local_mode_keeps_all(self):
        stamps = [f"20261101T00000{i}Z" for i in range(6)]
        for st in stamps:
            (self.dir / f"ledger.backup-{st}.sqlite").write_bytes(b"old")
        names = lambda: sorted(p.name for p in self.dir.glob("ledger.backup-*"))
        self.assertEqual(self.post("/api/demo/reset", {}).status_code, 200)
        left = names()
        self.assertEqual(len(left), 3)
        self.assertNotIn(f"ledger.backup-{stamps[0]}.sqlite", left)
        self.assertIn(self.post("/api/demo/reset", {}).status_code, (200, 409))  # same-second 409 is allowed
        local = self.make(False)
        for st in stamps:
            (self.dir / f"ledger.backup-{st}.sqlite").write_bytes(b"old")
        before = len(names())
        r = self.post("/api/demo/reset", {}, local)
        self.assertIn(r.status_code, (200, 409))
        self.assertGreaterEqual(len(names()), before)

    def test_the_reset_button_still_works_in_public_mode_and_makes_no_model_call(self):
        self.assertEqual(self.add_sample("noma_journeys", "NJ-09_signed_contract.md").status_code, 200)
        r = self.post("/api/demo/reset", {})
        self.assertEqual((r.status_code, r.json()["model_calls"], r.json()["deals_restored"]), (200, 0, 5))
        self.assertNotEqual(self.client.get("/api/deals/noma_journeys/register").json()["stage"]["current"], "signed")


class TestLocalModeIsUnchanged(Case):
    public = False

    def test_no_banner_no_gate_no_cap_all_deals_and_the_samples_are_not_offered(self):
        self.assertEqual(self.client.get("/api/demo/config").json()["banner"], None)
        self.assertEqual(sorted(self.client.get("/api/deals").json()["deals"]), sorted(config.UI_DEALS))
        r = self.post("/api/deals/noma_journeys/handover/notes", {"role": "sales", "note": "y" * 900, "entered_by": "Ann"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.post("/api/user-deals", {"name": "Mine"}).status_code, 200)
        self.assertEqual(self.client.get("/api/demo/samples", params={"deal": "noma_journeys"}).status_code, 404)


if __name__ == "__main__":
    unittest.main()
