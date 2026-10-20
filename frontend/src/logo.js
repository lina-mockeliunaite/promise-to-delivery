// Sizes for the Dealshape logo image (20 Oct). The wordmark's aspect is its viewBox, width / height (docs/brand/make_logo.py), and the
// image carries both numbers so the space is reserved before it loads and nothing moves. 21px high puts the wordmark's cap height at
// 11px, the cap height of the 15px semibold text it replaced, so the top bar keeps its size (its height is fixed at 48px).
export const LOGO_ASPECT = 310.127 / 64;
export const TOP_BAR_LOGO_HEIGHT = 21;
export const logoSize = (height) => ({ height, width: Math.round(height * LOGO_ASPECT * 10) / 10 });
