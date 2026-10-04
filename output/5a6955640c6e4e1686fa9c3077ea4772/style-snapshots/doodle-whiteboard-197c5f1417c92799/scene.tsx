import {makeScene2D} from '@revideo/2d';
import {waitFor} from '@revideo/core';
import {arrow, draw, note, popNote, star, underline, writeOn} from './helpers';
import {tokens} from './tokens';

export default makeScene2D('doodle-preview',function* (view) {
  view.fill(tokens.background);
  yield* writeOn(view,'Little ideas grow big',0,-350,88,1.0);
  yield* draw(view,underline([-500,-275],[500,-275]),.5);
  const items=[
    {x:-560,text:'SPARK',fill:tokens.pastels[0]},
    {x:0,text:'SKETCH',fill:tokens.pastels[1]},
    {x:560,text:'SHINE',fill:tokens.pastels[2]},
  ];
  for(let i=0;i<items.length;i++) {
    const item=items[i];
    yield* popNote(view,note(item.x,65,item.fill));
    yield* writeOn(view,item.text,item.x,65,57,.4);
    if(i<2) yield* draw(view,arrow([item.x+190,65],[item.x+365,65]),.3);
  }
  yield* draw(view,star(755,-218),.55);
  yield* writeOn(view,'Playful lines. Memorable stories.',0,345,51,.75);
  yield* waitFor(.9);
});
