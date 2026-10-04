import {makeScene2D} from '@revideo/2d';
import {waitFor} from '@revideo/core';
import {arrow, box, draw, line, numberedDot, underline, writeOn} from './helpers';
import {tokens} from './tokens';

export default makeScene2D('clean-preview', function* (view) {
  view.fill(tokens.background);
  yield* writeOn(view, 'A clear path forward', 0, -345, 82, 1.05);
  yield* draw(view, underline([-470,-275],[470,-275]), .55);
  const steps = [
    {x:-550, text:'Discover'}, {x:0, text:'Design'}, {x:550, text:'Deliver'},
  ];
  for (let i=0; i<steps.length; i++) {
    const {x,text} = steps[i];
    yield* draw(view, box(x,80,365,225), .7);
    const dot = numberedDot(x-134,-10,i+1);
    view.add(dot.ring); view.add(dot.label);
    yield* dot.ring.scale(1,.25);
    dot.label.opacity(1);
    yield* writeOn(view,text,x,105,50,.45);
    if (i<2) yield* draw(view,arrow([x+205,80],[x+345,80]),.4);
  }
  // The small diagram icon is built from a sequence of drawn strokes.
  yield* draw(view,line([[680,-215],[710,-245],[740,-215],[710,-185],[680,-215]],tokens.accent,5),.45);
  yield* draw(view,line([[710,-245],[710,-185]],tokens.slate,3),.22);
  yield* writeOn(view,'One idea, three practical steps.',0,345,47,.85);
  yield* waitFor(1.5);
});
