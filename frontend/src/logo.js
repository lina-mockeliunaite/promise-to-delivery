// Sizes for the Dealshape logo image (20 Oct). The wordmark's aspect is its viewBox, width / height (docs/brand/make_logo.py), and the
// image carries both numbers so the space is reserved before it loads and nothing moves. 21px high puts the wordmark's cap height at
// 11px, the cap height of the 15px semibold text it replaced, so the top bar keeps its size (its height is the --topbar-h variable, 56px, in DealPage.css).
export const LOGO_ASPECT = 310.127 / 64;
export const TOP_BAR_LOGO_HEIGHT = 21;
// Where the wordmark's text starts, in viewBox units: the left edge of the "D" of "Dealshape" (the mark and the gap come before it). The
// tagline under the logo is indented by this much, so its left edge lines up with the text, not with the mark.
export const WORDMARK_TEXT_X = 82.383;
export const wordmarkTextOffset = (height) => Math.round((WORDMARK_TEXT_X * height / 64) * 10) / 10;
export const logoSize = (height) => ({ height, width: Math.round(height * LOGO_ASPECT * 10) / 10 });
