import {Circle, Line, Txt, View2D} from '@revideo/2d';
import {easeInOutCubic, ThreadGenerator} from '@revideo/core';
import {tokens} from './tokens';

type Point = [number, number];

export function line(points: Point[], color: string = tokens.ink, width: number = tokens.strokeWidth): Line {
  const subtle = points.flatMap((point, index) => {
    if (!index) return [point];
    const before = points[index-1];
    return [[(before[0]+point[0])/2, (before[1]+point[1])/2 + (index%2 ? tokens.wobble : -tokens.wobble)] as Point, point];
  });
  return new Line({points: subtle, stroke: color, lineWidth: width, lineCap: 'round', lineJoin: 'round', end: 0});
}

export function box(x: number, y: number, w: number, h: number): Line {
  return line([[x-w/2,y-h/2],[x+w/2,y-h/2],[x+w/2,y+h/2],[x-w/2,y+h/2],[x-w/2,y-h/2]]);
}

export function arrow(start: Point, end: Point): Line {
  const shape = line([start, end], tokens.slate, 4);
  shape.endArrow(true); shape.arrowSize(16);
  return shape;
}

export function underline(start: Point, end: Point): Line { return line([start,end], tokens.accent, 6); }

export function numberedDot(x: number, y: number, number: number): {ring: Circle; label: Txt} {
  return {
    ring: new Circle({x,y,size:58,stroke:tokens.accent,lineWidth:4,fill:tokens.background,scale:0}),
    label: new Txt({text:String(number),x,y,fill:tokens.accent,fontFamily:tokens.fontFamily,fontSize:29,fontWeight:700,opacity:0}),
  };
}

export function* draw(view: View2D, shape: Line, seconds = .6): ThreadGenerator {
  view.add(shape);
  yield* shape.end(1, seconds, easeInOutCubic);
}

export function* writeOn(view: View2D, text: string, x: number, y: number, size: number, seconds = .8): ThreadGenerator {
  const label = new Txt({text:'',x,y,fill:tokens.ink,fontFamily:tokens.fontFamily,fontSize:size,fontWeight:600});
  view.add(label);
  yield* label.text(text, seconds);
}
