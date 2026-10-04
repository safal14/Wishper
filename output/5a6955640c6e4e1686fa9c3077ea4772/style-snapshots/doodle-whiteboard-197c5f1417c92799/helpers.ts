import {Line, Rect, Txt, View2D} from '@revideo/2d';
import {easeInOutCubic, easeOutBack, ThreadGenerator} from '@revideo/core';
import {tokens} from './tokens';

type Point = [number, number];

export function line(points: Point[], color: string = tokens.ink, width: number = tokens.strokeWidth): Line {
  const bent: Point[] = [];
  points.forEach((point,index) => {
    if (index) {
      const before = points[index-1];
      bent.push([(before[0]+point[0])/2+(index%2?tokens.wobble:-tokens.wobble),
        (before[1]+point[1])/2+(index%2?-tokens.wobble:tokens.wobble)]);
    }
    bent.push(point);
  });
  return new Line({points:bent,stroke:color,lineWidth:width,lineCap:'round',lineJoin:'round',end:0});
}

export function note(x: number,y: number,color: string): {paper: Rect; outline: Line} {
  const w=350,h=225;
  return {
    paper:new Rect({x,y,width:w,height:h,fill:color,rotation:-3,scale:0}),
    outline:line([[x-w/2,y-h/2],[x+w/2,y-h/2],[x+w/2,y+h/2],[x-w/2,y+h/2],[x-w/2,y-h/2]]),
  };
}

export function arrow(start: Point,end: Point): Line {
  const result=line([start,end],tokens.accent,8);
  result.endArrow(true); result.arrowSize(22);
  return result;
}

export function underline(start: Point,end: Point): Line { return line([start,end],tokens.accent,13); }

export function star(x: number,y: number): Line {
  return line([[x,y-65],[x+18,y-18],[x+70,y-18],[x+29,y+11],[x+44,y+63],[x,y+34],[x-44,y+63],[x-29,y+11],[x-70,y-18],[x-18,y-18],[x,y-65]],tokens.accent,9);
}

export function* draw(view: View2D, shape: Line, seconds = .5): ThreadGenerator {
  view.add(shape);
  yield* shape.end(1,seconds,easeInOutCubic);
}

export function* popNote(view: View2D, item: {paper: Rect; outline: Line}): ThreadGenerator {
  view.add(item.paper);
  yield* item.paper.scale(1,.3,easeOutBack);
  yield* draw(view,item.outline,.5);
  yield* item.paper.rotation(2,.16).to(-3,.16);
}

export function* writeOn(view: View2D, text: string,x: number,y: number,size: number,seconds=.8): ThreadGenerator {
  const label=new Txt({text:'',x,y,fill:tokens.ink,fontFamily:tokens.fontFamily,fontSize:size,fontWeight:700});
  view.add(label);
  yield* label.text(text,seconds);
}
