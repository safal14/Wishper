export const tokens = {
  background: '#FFFFFF', ink: '#16191D', accents: ['#2266D8', '#E44442', '#249962', '#E88A22'],
  fontFamily: 'Wishper Marker Stroke', // Vector glyphs are drawn by helpers.writeOn.
  strokeWidth: 11, wobble: 7, writeOnSpeed: 20,
  easing: 'quick-hand', drawOrder: ['title', 'underline', 'boxes', 'arrows', 'icon', 'caption'],
} as const;
