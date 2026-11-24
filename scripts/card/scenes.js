/* Встроенные зимние истории. Только SVG: без загрузок, сетевых запросов и финансовых данных. */
(function (root) {
  'use strict';
  const C = {cream:'#fff5dc', red:'#ef6269', gold:'#f3ca69', mint:'#76c8ae', pine:'#347c70',
    blue:'#8ebcda', lilac:'#b5a0d6', ink:'#253955', snow:'#edf7fc', wood:'#bd8064'};
  const rect = (x,y,w,h,r,fill,extra='') => `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${r}" fill="${fill}" ${extra}/>`;
  const circle = (x,y,r,fill,extra='') => `<circle cx="${x}" cy="${y}" r="${r}" fill="${fill}" ${extra}/>`;
  const ellipse = (x,y,rx,ry,fill,extra='') => `<ellipse cx="${x}" cy="${y}" rx="${rx}" ry="${ry}" fill="${fill}" ${extra}/>`;
  const path = (d,fill,extra='') => `<path d="${d}" fill="${fill}" ${extra}/>`;
  const line = (x1,y1,x2,y2,color,width=4) => `<path d="M${x1} ${y1}L${x2} ${y2}" stroke="${color}" stroke-width="${width}" stroke-linecap="round"/>`;
  const group = (x,y,s,body) => `<g transform="translate(${x} ${y}) scale(${s})">${body}</g>`;
  function star(x,y,s,color=C.gold) {
    return group(x,y,s,path('M0-23 7-7 25-7 11 4 16 22 0 12-16 22-11 4-25-7-7-7Z',color));
  }
  function pine(x,y,s=1,color=C.pine,decorated=true) {
    return group(x,y,s,rect(-7,103,14,25,3,C.wood) +
      path('M0 0 31 42 20 42 45 77 29 77 58 116-58 116-29 77-45 77-20 42-31 42Z',color) +
      (decorated ? star(0,0,.34) + [[-10,38,C.red],[16,65,C.cream],[-20,89,C.gold],[20,101,C.red],[1,81,C.blue]]
        .map(([a,b,c])=>circle(a,b,4,c)).join('') : ''));
  }
  function gift(x,y,s=1,color=C.red,ribbon=C.gold) {
    return group(x,y,s,rect(0,23,95,78,8,color)+rect(-5,15,105,21,5,color)+
      rect(40,15,14,86,1,ribbon)+path('M47 15C12 20 3-13 22-9 34-7 45 9 47 15ZM47 15C82 20 91-13 72-9 60-7 49 9 47 15Z',ribbon));
  }
  function windowPane(x,y,w=270,h=230) {
    return rect(x-10,y-10,w+20,h+20,26,C.wood)+rect(x,y,w,h,18,'#436781')+
      circle(x+w*.72,y+43,22,C.cream)+path(`M${x} ${y+h-35}Q${x+w*.4} ${y+h-85} ${x+w} ${y+h-34}V${y+h}H${x}Z`,C.snow)+
      line(x+w/2,y,x+w/2,y+h,C.cream,9)+line(x,y+h*.52,x+w,y+h*.52,C.cream,9)+
      rect(x-19,y+h-2,w+38,13,6,C.cream);
  }
  function table(y=340) {
    return rect(155,y+15,24,105,7,C.wood)+rect(896,y+15,24,105,7,C.wood)+
      rect(108,y,864,24,12,'#dcac8a')+rect(115,y,850,7,3,C.cream);
  }
  function mug(x,y,s=1,color=C.red) {
    return group(x,y,s,path('M111 12C165-2 162 83 111 67','none',`stroke="${color}" stroke-width="17"`)+
      path('M0 0H118V65Q118 103 79 103H39Q0 103 0 65Z',color)+ellipse(59,3,59,14,C.cream)+
      ellipse(59,4,47,8,'#aa6b4e')+star(57,54,.65,C.cream)+
      path('M30-28C12-50 48-58 31-81M72-28C54-50 90-58 73-81','none',
        'stroke="#fff5dc" stroke-width="6" stroke-linecap="round" opacity=".65"'));
  }
  function book(x,y,s=1,color=C.red) {
    return group(x,y,s,rect(0,0,142,29,5,color)+rect(7,6,129,16,2,C.cream)+line(15,12,124,12,'#c7ad92',2));
  }
  function house(x,y,s=1,color=C.red) {
    return group(x,y,s,rect(0,84,190,218,9,color)+path('M-18 90 95 0 208 90Z',C.ink)+
      path('M-20 90 95-3 210 90','none','stroke="#edf7fc" stroke-width="14" stroke-linejoin="round"')+
      rect(22,119,55,64,8,C.gold)+rect(113,119,55,64,8,C.gold)+
      line(49,120,49,182,C.cream,5)+line(140,120,140,182,C.cream,5)+
      rect(73,224,48,78,10,C.pine)+circle(108,267,3,C.gold)+rect(-12,296,214,12,6,C.snow));
  }
  function teddy(x,y,s=1) {
    return group(x,y,s,circle(-46,9,28,'#b67c58')+circle(46,9,28,'#b67c58')+
      circle(-46,9,15,'#ecc5a1')+circle(46,9,15,'#ecc5a1')+
      ellipse(0,126,64,77,'#c99368')+ellipse(0,131,35,47,'#ecc5a1')+
      ellipse(-56,111,24,43,'#c99368')+ellipse(56,111,24,43,'#c99368')+
      ellipse(-35,190,32,23,'#b67c58')+ellipse(35,190,32,23,'#b67c58')+
      circle(0,48,63,'#c99368')+ellipse(0,67,29,23,'#f0d1ae')+
      circle(-21,40,6,C.ink)+circle(21,40,6,C.ink)+ellipse(0,58,9,6,C.ink)+
      path('M-12 76Q0 88 12 76','none',`stroke="${C.ink}" stroke-width="3" stroke-linecap="round"`)+
      rect(-54,92,108,22,9,C.red)+rect(24,105,22,59,6,C.red)+line(29,147,40,147,C.cream,4));
  }
  function snowman(x,y,s=1) {
    return group(x,y,s,circle(0,86,57,C.snow)+circle(0,7,40,C.cream)+
      rect(-45,-29,90,12,5,C.ink)+rect(-28,-72,56,47,7,C.ink)+rect(-28,-40,56,12,2,C.red)+
      circle(-13,2,4,C.ink)+circle(13,2,4,C.ink)+path('M-1 12 28 18-1 25Z',C.red)+
      path('M-13 30Q0 39 13 30','none',`stroke="${C.ink}" stroke-width="3"`)+
      rect(-40,43,80,14,6,C.red)+rect(22,51,15,46,4,C.red)+
      circle(0,80,4,C.ink)+circle(0,104,4,C.ink)+line(-48,75,-94,40,C.wood,6)+line(48,75,94,35,C.wood,6));
  }
  function sprig(x,y,s=1) {
    return group(x,y,s,line(0,0,76,-95,C.pine,5)+[20,38,56].map(a=>
      path(`M${a*.8} ${-a}q-39-4-32-28 26 1 32 28m0 0q35 5 37-18-24-8-37 18`,C.pine)).join('')+
      circle(14,-42,8,C.red)+circle(52,-77,7,C.red));
  }
  function parfait(x,y,s=1,color=C.red,variant=0) {
    return group(x,y,s,ellipse(0,172,66,11,'#253955','opacity=".15"')+
      path('M-65 0H65L45 156Q0 180-45 156Z',C.cream)+
      path('M-59 37H59L54 75Q0 94-54 75Z',color)+
      path('M-51 98H51L45 139Q0 160-45 139Z',color)+
      path('M-65 0H65L45 156Q0 180-45 156Z','none','stroke="#c3e3e9" stroke-width="5"')+
      ellipse(0,0,65,14,C.cream)+[[-32,-13],[0,-22],[30,-13]].map(([a,b],i)=>circle(a,b,16,i===variant%3?C.gold:color)).join('')+
      path('M-7-31q4-28 25-21-3 21-25 21',C.pine)+line(-43,30,-34,102,'#fff',6));
  }
  function person(x,y,color,child=false) {
    return group(x,y,child ? .72 : 1,rect(-34,23,68,86,26,color)+circle(0,0,26,'#f2cfb0')+
      path('M-26-4Q-25-36 3-29 28-27 27-3 6-20-26-4',C.ink)+
      circle(-9,2,2.6,C.ink)+circle(9,2,2.6,C.ink)+path('M-7 13Q0 19 7 13','none',`stroke="${C.ink}" stroke-width="2.5" stroke-linecap="round"`));
  }
  function winterBase(seed) {
    let state=Math.abs(seed)%233280;
    const rnd=()=> (state=(state*9301+49297)%233280)/233280;
    return ellipse(540,205,445,200,'url(#glow)')+
      Array.from({length:36},()=>circle(36+rnd()*1008,15+rnd()*365,1.5+rnd()*2.2,C.cream,`opacity="${.25+rnd()*.45}"`)).join('')+
      path('M0 412Q180 370 350 410T700 411T1080 405V460H0Z',C.snow)+ellipse(540,429,410,18,'#cadae4','opacity=".4"');
  }
  const SCENES = {
    gift: {id:'gift-workshop', title:'Мастерская подарков', top:'#315568', bottom:'#173047', draw(v) {
      return windowPane(413,28,245,222)+line(163,0,163,119,C.gold,3)+line(860,0,860,89,C.gold,3)+
        star(163,135,1.1)+star(860,105,.8,C.cream)+table(352)+gift(220,235,1.05,[C.red,C.lilac,C.mint][v])+
        gift(675,199,1.4,C.pine)+gift(497,277,.65,C.lilac)+
        rect(387,323,64,28,7,C.gold)+ellipse(419,323,32,8,C.cream)+
        path('M475 342 541 315M482 318 538 345','none',`stroke="${C.ink}" stroke-width="5" stroke-linecap="round"`)+
        circle(464,345,11,'none',`stroke="${C.red}" stroke-width="5"`)+circle(473,316,11,'none',`stroke="${C.red}" stroke-width="5"`);
    }},
    heart: {id:'warm-windows', title:'Тёплые окна', top:'#455574', bottom:'#23334e', draw(v) {
      return pine(120,136,1.8,C.pine,false)+pine(926,156,1.6,C.pine,false)+
        house(180,174,.75,C.lilac)+house(407,75,1.05,[C.red,C.pine,C.wood][v])+house(744,187,.72,C.blue)+
        circle(508,308,24,C.pine)+circle(508,308,13,C.red)+star(508,306,.35,C.cream)+
        path('M303 424q130-55 235 0','none','stroke="#c7dce8" stroke-width="6" stroke-linecap="round" stroke-dasharray="5 22"')+
        star(790,66,.6)+star(289,69,.38,C.cream);
    }},
    smile: {id:'snowy-street', title:'Снежная улица', top:'#355e79', bottom:'#1c3957', draw(v) {
      return house(290,90,1.03,[C.lilac,C.red,C.wood][v])+house(602,150,.84,C.pine)+pine(931,182,1.8,C.pine,false)+
        line(136,100,136,404,C.ink,13)+rect(111,399,50,12,6,C.ink)+
        rect(109,41,54,72,12,C.gold)+rect(117,50,38,52,6,C.cream)+path('M100 44 136 15 172 44Z',C.ink)+
        circle(136,78,73,C.gold,'opacity=".07"')+snowman(808,307,.76)+star(610,64,.55);
    }},
    snowflake: {id:'snow-globe', title:'Снежный шар', top:'#344f7d', bottom:'#233258', draw(v) {
      return circle(540,211,184,'#759fbc','fill-opacity=".35" stroke="#d6eff8" stroke-width="7"')+
        path('M369 282Q500 231 706 276Q702 360 618 382H461Q392 350 369 282Z',C.snow)+
        pine(433,203,1,C.pine,false)+pine(651,166,1.25,C.pine,false)+house(486,179,.51,[C.red,C.lilac,C.wood][v])+
        circle(456,111,8,C.cream)+circle(590,82,5,C.cream)+circle(667,136,6,C.cream)+circle(606,280,5,C.cream)+
        path('M406 175Q419 101 479 67','none','stroke="#fff5dc" stroke-width="13" stroke-linecap="round" opacity=".55"')+
        rect(420,371,240,54,18,C.wood)+rect(401,411,278,20,10,'#e1b894')+star(540,397,.5)+
        star(249,172,.7,C.cream)+star(830,120,.8,C.cream)+pine(203,275,1.1,C.pine,false)+pine(873,265,1.25,C.pine,false);
    }},
    candy: {id:'sweet-shop', title:'Лавка сладостей', top:'#4c4b70', bottom:'#283650', draw(v) {
      const jars=[C.red,C.lilac,C.mint];
      return rect(211,127,658,258,25,C.cream)+rect(246,164,588,183,12,'#e8d3c3')+
        rect(196,63,688,69,10,C.red)+Array.from({length:10},(_,i)=>
          path(`M${199+i*68} 63h34v59q-17 36-34 0Z`,C.cream)).join('')+
        rect(187,368,706,32,10,C.wood)+[360,540,720].map((x,i)=>
          rect(x-52,213,104,142,17,'#eaf4ef')+rect(x-57,204,114,21,7,jars[(i+v)%3])+
          [0,1,2,3,4,5].map(n=>circle(x-26+(n%2)*50,253+Math.floor(n/2)*35,14,jars[(i+n)%3])).join('')).join('')+
        pine(130,239,1.4)+gift(886,338,.7,C.lilac)+star(540,27,.8);
    }},
    family: {id:'family-evening', title:'Вечер в гостиной', top:'#375c59', bottom:'#1b383f', draw(v) {
      return windowPane(732,28,208,232)+rect(177,215,404,169,40,C.pine)+rect(156,272,67,119,25,C.mint)+
        rect(544,272,67,119,25,C.mint)+rect(227,331,309,55,19,'#28665e')+
        person(291,216,C.red)+person(472,216,C.lilac)+person(383,267,[C.gold,C.blue,C.red][v],true)+
        path('M330 308Q374 290 409 308V354Q371 335 330 354Z',C.cream)+
        path('M409 308Q443 290 476 304V349Q438 337 409 354Z','#e5d5ba')+line(409,310,409,353,C.wood,3)+
        line(110,124,110,376,C.gold,7)+path('M45 137 73 59 145 59 176 137Z',C.cream)+
        rect(764,350,179,19,7,C.wood)+rect(837,366,15,63,4,C.wood)+mug(798,292,.5,C.red)+
        ellipse(392,421,268,24,'#be9e9c','opacity=".6"');
    }},
    tree: {id:'tree-square', title:'Ёлка на площади', top:'#284e66', bottom:'#183749', draw(v) {
      return house(126,208,.65,C.wood)+house(814,190,.7,C.lilac)+
        pine(540,23,3.12,[C.pine,'#438e79','#427c73'][v])+snowman(840,339,.55)+
        rect(187,361,180,17,5,C.wood)+rect(187,332,180,14,4,C.wood)+
        line(207,379,207,416,C.ink,7)+line(347,379,347,416,C.ink,7)+
        gift(417,343,.7,C.red)+gift(583,348,.63,C.lilac)+star(293,102,.7,C.cream)+star(805,97,.55,C.gold);
    }},
    star: {id:'star-studio', title:'Мастерская звёзд', top:'#4e5177', bottom:'#293754', draw(v) {
      return windowPane(391,22,300,242)+[190,319,770,889].map((x,i)=>
        line(x,0,x,58+i%2*60,C.gold,2)+star(x,94+i%2*60,[1.5,.7,1.3,.75][i],[C.gold,C.cream,C.red,C.cream][i])).join('')+
        table(356)+path('M278 316 438 292 478 344 314 349Z',C.cream)+
        star(373,324,.8,[C.gold,C.red,C.lilac][v])+star(600,322,1.05,C.red)+
        rect(725,296,65,58,9,C.wood)+[0,1,2,3].map(i=>line(738+i*13,300,735+i*13,248,[C.red,C.gold,C.lilac,C.mint][i],7)).join('')+
        circle(508,329,5,C.red)+circle(520,347,5,C.gold)+circle(538,331,5,C.mint);
    }},
    tea: {id:'tea-by-window', title:'Чай у окна', top:'#55465e', bottom:'#30364d', draw(v) {
      return windowPane(402,25,279,235)+table(353)+book(218,313,.94,C.lilac)+book(231,287,.85,C.pine)+
        mug(479,228,1.12,[C.red,C.pine,C.lilac][v])+ellipse(545,355,108,13,C.cream)+
        ellipse(775,281,65,66,C.mint)+rect(747,211,56,16,7,C.pine)+circle(775,204,9,C.gold)+
        path('M825 264q72-48 58 13-12 38-45 31','none',`stroke="${C.mint}" stroke-width="19"`)+
        path('M713 264 677 233 685 295 721 310Z',C.mint)+sprig(177,350,.9)+
        ellipse(771,350,47,8,C.pine)+star(240,95,.6,C.gold);
    }},
    cake: {id:'dessert-kitchen', title:'Кухня с десертами', top:'#59516a', bottom:'#33384e', draw(v) {
      return windowPane(385,22,303,220)+rect(153,150,151,12,5,C.wood)+rect(775,150,150,12,5,C.wood)+
        [185,239,806,861].map((x,i)=>rect(x,91,35,58,7,[C.cream,C.red,C.mint,C.cream][i])+rect(x-3,84,41,12,4,C.gold)).join('')+
        table(363)+parfait(327,196,.92,C.red,v)+parfait(540,150,1.15,[C.lilac,C.red,'#e7b84e'][v],v)+
        parfait(757,196,.92,C.mint,v)+sprig(168,345,.8)+star(868,47,.64,C.gold);
    }},
    toy: {id:'toy-workshop', title:'Игрушечная мастерская', top:'#455977', bottom:'#273b56', draw(v) {
      return windowPane(694,29,224,225)+rect(144,166,223,16,5,C.wood)+gift(172,96,.6,C.lilac)+
        star(302,126,.95,C.gold)+table(367)+teddy(527,87,1.3)+gift(749,271,.95,[C.red,C.lilac,C.mint][v])+
        rect(208,311,139,36,8,C.pine)+rect(225,281,54,34,7,C.red)+rect(216,272,73,12,4,C.gold)+
        [237,318].map(x=>circle(x,351,17,C.ink)+circle(x,351,8,C.gold)).join('')+circle(337,304,12,C.gold);
    }},
    pancakes: {id:'winter-breakfast', title:'Зимний завтрак', top:'#4b5d68', bottom:'#293c4c', draw(v) {
      return windowPane(393,20,294,221)+table(373)+ellipse(536,353,228,38,C.blue)+ellipse(536,343,210,27,C.cream)+
        [0,1,2].map(i=>rect(390,288-i*21,292,26,13,'#c68c4b')+ellipse(536,285-i*21,146,24,'#efbf74')).join('')+
        path('M425 245q30-25 66-10t65-2q48-8 91 14l-15 21q-11 13-19-1-10-13-16 13-12 24-21-5-9-16-28-1-30 17-51-9-25-19-58 0Z','#b26c3c')+
        rect(510,218,47,24,6,C.gold)+[[-31,-12],[0,-28],[29,-9]].map(([x,y])=>circle(537+x,216+y,13,[C.red,C.lilac,C.red][v])).join('')+
        mug(795,285,.58,C.red)+sprig(193,359,.9)+star(211,91,.55,C.gold);
    }}
  };
  function build(icon,seed=7) {
    const numeric=Number.isFinite(Number(seed))?Math.abs(Math.floor(Number(seed))):7;
    const key=Object.hasOwn ? (Object.hasOwn(SCENES,icon)?icon:'gift') :
      (Object.prototype.hasOwnProperty.call(SCENES,icon)?icon:'gift');
    const item=SCENES[key], variant=numeric%3;
    const svg=`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1080 460" role="img" aria-label="${item.title}"><defs>`+
      '<radialGradient id="glow"><stop offset="0" stop-color="#fff2cd" stop-opacity=".17"/><stop offset="1" stop-color="#fff2cd" stop-opacity="0"/></radialGradient>'+
      `</defs>${winterBase(numeric)}${item.draw(variant)}</svg>`;
    return {id:item.id,title:item.title,top:item.top,bottom:item.bottom,variant,svg};
  }
  const api={build,icons:Object.keys(SCENES)};
  if (typeof module!=='undefined' && module.exports) module.exports=api;
  root.NGScenes=api;
})(typeof window!=='undefined'?window:globalThis);
