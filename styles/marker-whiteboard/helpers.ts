import {Circle, Line, View2D} from '@revideo/2d';
import {easeInOutCubic, ThreadGenerator} from '@revideo/core';
import {tokens} from './tokens';

type Point = [number, number];

// Deterministic bends keep the same hand-drawn geometry on every render.
export function wobbly(points: Point[], amount: number = tokens.wobble): Point[] {
  const out: Point[] = [];
  points.forEach((point, index) => {
    if (index) {
      const previous = points[index - 1];
      out.push([(previous[0] + point[0]) / 2 + (index % 2 ? amount : -amount),
        (previous[1] + point[1]) / 2 + (index % 2 ? -amount : amount)]);
    }
    out.push(point);
  });
  return out;
}

export function line(points: Point[], color: string = tokens.ink, width: number = tokens.strokeWidth): Line {
  return new Line({points: wobbly(points), stroke: color, lineWidth: width, lineCap: 'round', lineJoin: 'round', end: 0});
}

export function box(x: number, y: number, width: number, height: number, color: string = tokens.ink): Line {
  return line([[x-width/2,y-height/2],[x+width/2,y-height/2],[x+width/2,y+height/2],[x-width/2,y+height/2],[x-width/2,y-height/2]], color);
}

export function arrow(from: Point, to: Point, color: string = tokens.ink): Line {
  const result = line([from, to], color, tokens.strokeWidth-2);
  result.endArrow(true);
  result.arrowSize(22);
  return result;
}

export function underline(from: Point, to: Point, color = tokens.accents[0]): Line {
  return line([from, to], color, tokens.strokeWidth+3);
}

export function markerCursor(): Circle {
  return new Circle({size: 28, fill: tokens.ink, stroke: tokens.background, lineWidth: 5, opacity: 0});
}

export function* draw(view: View2D, stroke: Line, seconds: number, cursor?: Circle): ThreadGenerator {
  view.add(stroke);
  if (cursor) {
    cursor.position(() => stroke.getPointAtPercentage(stroke.end()).position);
    cursor.opacity(1);
    cursor.moveToTop();
  }
  yield* stroke.end(1, seconds, easeInOutCubic);
  if (cursor) cursor.opacity(0);
}

// A single-line marker alphabet. Each nested path is one pen-down stroke.
const glyphs: Record<string, number[][][]> = {
  A: [[[0,1],[.5,0],[1,1]],[[.2,.6],[.8,.6]]],
  B: [[[0,0],[0,1]],[[0,0],[.7,0],[1,.2],[.7,.48],[0,.48]],[[0,.48],[.75,.48],[1,.73],[.75,1],[0,1]]],
  C: [[[1,.1],[.7,0],[.2,0],[0,.25],[0,.75],[.2,1],[.7,1],[1,.9]]],
  D: [[[0,0],[0,1]],[[0,0],[.7,0],[1,.3],[1,.7],[.7,1],[0,1]]],
  E: [[[1,0],[0,0],[0,1],[1,1]],[[0,.5],[.75,.5]]],
  F: [[[0,1],[0,0],[1,0]],[[0,.5],[.75,.5]]],
  G: [[[1,.15],[.7,0],[.2,0],[0,.25],[0,.75],[.2,1],[.8,1],[1,.72],[1,.55],[.55,.55]]],
  H: [[[0,0],[0,1]],[[1,0],[1,1]],[[0,.5],[1,.5]]],
  I: [[[0,0],[1,0]],[[.5,0],[.5,1]],[[0,1],[1,1]]],
  J: [[[.1,.8],[.3,1],[.75,1],[1,.75],[1,0]]],
  K: [[[0,0],[0,1]],[[1,0],[0,.55],[1,1]]],
  L: [[[0,0],[0,1],[1,1]]],
  M: [[[0,1],[0,0],[.5,.55],[1,0],[1,1]]],
  N: [[[0,1],[0,0],[1,1],[1,0]]],
  O: [[[.2,0],[.8,0],[1,.25],[1,.75],[.8,1],[.2,1],[0,.75],[0,.25],[.2,0]]],
  P: [[[0,1],[0,0],[.75,0],[1,.25],[.75,.5],[0,.5]]],
  Q: [[[.2,0],[.8,0],[1,.25],[1,.75],[.8,1],[.2,1],[0,.75],[0,.25],[.2,0]],[[.6,.7],[1.1,1.1]]],
  R: [[[0,1],[0,0],[.75,0],[1,.25],[.75,.5],[0,.5]],[[.5,.5],[1,1]]],
  S: [[[1,.1],[.7,0],[.2,0],[0,.25],[.2,.5],[.8,.5],[1,.75],[.8,1],[.2,1],[0,.9]]],
  T: [[[0,0],[1,0]],[[.5,0],[.5,1]]],
  U: [[[0,0],[0,.75],[.2,1],[.8,1],[1,.75],[1,0]]],
  V: [[[0,0],[.5,1],[1,0]]],
  W: [[[0,0],[.2,1],[.5,.5],[.8,1],[1,0]]],
  X: [[[0,0],[1,1]],[[1,0],[0,1]]],
  Y: [[[0,0],[.5,.5],[1,0]],[[.5,.5],[.5,1]]],
  Z: [[[0,0],[1,0],[0,1],[1,1]]],
  '1': [[[.2,.25],[.5,0],[.5,1]],[[.2,1],[.8,1]]],
  '2': [[[0,.2],[.2,0],[.8,0],[1,.2],[1,.4],[0,1],[1,1]]],
  '3': [[[0,.1],[.25,0],[.8,0],[1,.2],[.8,.5],[.3,.5]],[[.8,.5],[1,.8],[.8,1],[.25,1],[0,.9]]],
  '.': [[[.5,.9],[.5,1]]],
};

export function* writeOn(
  view: View2D, value: string, x: number, y: number, size: number,
  color: string = tokens.ink, seconds = 0.8, cursor?: Circle,
): ThreadGenerator {
  const letters = [...value.toUpperCase()];
  const advance = size * .72;
  const totalWidth = letters.reduce((width, letter) => width + (letter === ' ' ? size*.38 : advance), 0);
  const strokeCount = letters.reduce((count, letter) => count + (glyphs[letter]?.length || 0), 0);
  let left = x - totalWidth/2;
  for (const letter of letters) {
    if (letter === ' ') { left += size*.38; continue; }
    for (const stroke of glyphs[letter] || []) {
      const points = stroke.map(([gx,gy]) => [left + gx*size*.58, y + (gy-.5)*size] as Point);
      yield* draw(view, new Line({points:wobbly(points,size*.012),stroke:color,lineWidth:Math.max(3.5,size*.065),lineCap:'round',lineJoin:'round',end:0}), seconds/Math.max(strokeCount,1), cursor);
    }
    left += advance;
  }
}
