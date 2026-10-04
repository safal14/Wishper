import {makeScene2D} from '@revideo/2d';
import {waitFor} from '@revideo/core';
import {arrow, box, draw, line, markerCursor, underline, writeOn} from './helpers';
import {tokens} from './tokens';

export default makeScene2D('marker-preview', function* (view) {
  view.fill(tokens.background);
  const cursor = markerCursor();
  view.add(cursor);
  yield* writeOn(view, 'Make the idea visible', 0, -345, 86, tokens.ink, 1.1, cursor);
  yield* draw(view, underline([-540,-275], [540,-275]), .45, cursor);

  const items = [
    {x:-570, label:'1  ASK', color:tokens.accents[0]},
    {x:0, label:'2  DRAW', color:tokens.accents[1]},
    {x:570, label:'3  SHARE', color:tokens.accents[2]},
  ];
  for (let i=0; i<items.length; i++) {
    const item = items[i];
    yield* draw(view, box(item.x, 65, 350, 220, item.color), .65, cursor);
    yield* writeOn(view, item.label, item.x, 65, 60, tokens.ink, .45, cursor);
    if (i<2) yield* draw(view, arrow([item.x+190,65], [item.x+375,65], tokens.accents[3]), .35, cursor);
  }
  // A quick spark doodle is drawn as separate marker strokes.
  for (const ray of [
    [[735,-225],[735,-170]], [[685,-195],[705,-155]], [[785,-195],[765,-155]],
  ] as [number,number][][]) yield* draw(view, line(ray, tokens.accents[3], 9), .18, cursor);
  yield* writeOn(view, 'Bold ideas. Drawn into motion.', 0, 345, 52, tokens.ink, .8, cursor);
  yield* waitFor(1.2);
});
