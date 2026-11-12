"""Native Visio renderer/checker. JSON content is independent of COM mechanics."""
import argparse
import hashlib
import json
import math
import re
import struct
import sys
import zipfile
from pathlib import Path

STYLE = dict(font='宋体', math_font='Cambria Math', node_pt=28, formula_pt=25,
             note_pt=22, title_pt=40, line_pt=1.5)
PALETTE = dict(ink='#203641', muted='#536773', green='#16755F', green_fill='#EDF6F1',
               blue='#22659B', blue_fill='#EAF2FB', purple='#68518A', purple_fill='#F3EFF8',
               orange='#B5792D', white='#FFFFFF', rule='#CEDBD7')


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def markup(value):
    """Return plain string and UTF-16 sub/superscript spans, not LaTeX."""
    value = str(value)
    plain, runs, end = '', [], 0
    for m in re.finditer(r'([_^])\{([^{}]*)\}', value):
        preceding = value[end:m.start()]
        if re.search(r'[_^]\{', preceding):
            raise ValueError('Nested or malformed math markup: '+value)
        plain += preceding
        start = len(plain.encode('utf-16-le'))//2
        plain += m[2]
        runs.append((start, len(plain.encode('utf-16-le'))//2, 2 if m[1]=='_' else 1))
        end = m.end()
    tail = value[end:]
    if re.search(r'[_^]\{', tail):
        raise ValueError('Nested or malformed math markup: '+value)
    return plain+tail, runs


def box(x, y, w, h):
    return [x-w/2, y-h/2, x+w/2, y+h/2]


def overlap(a, b, eps=.015):
    return min(a[2],b[2])-max(a[0],b[0])>eps and min(a[3],b[3])-max(a[1],b[1])>eps


def segment_hits(a, b, rect):
    # Liang-Barsky clipping against the open interior, including bridge chords.
    l,t,r,d = rect; l+=.02; t+=.02; r-=.02; d-=.02
    if l>=r or t>=d:
        return False
    lo,hi = 0.,1.
    dx,dy = b[0]-a[0], b[1]-a[1]
    for p,q in ((-dx,a[0]-l),(dx,r-a[0]),(-dy,a[1]-t),(dy,d-a[1])):
        if abs(p)<1e-12:
            if q<0: return False
        elif p<0: lo=max(lo,q/p)
        else: hi=min(hi,q/p)
        if lo>hi: return False
    return hi-lo>1e-6


def port(node, side, offset=0):
    x,y,w,h = node['x'],node['y'],node.get('w',4.5),node.get('h',.84)
    if side not in 'lrtb' or len(side)!=1:
        raise ValueError('Port must be l/r/t/b')
    if abs(offset) > (h if side in 'lr' else w)/2:
        raise ValueError('Port offset outside node: '+node['id'])
    return dict(l=(x-w/2,y+offset),r=(x+w/2,y+offset),t=(x+offset,y-h/2),b=(x+offset,y+h/2))[side]


def route(edge, nodes):
    a=port(nodes[edge['from']],edge.get('from_port','r'),edge.get('from_offset',0))
    b=port(nodes[edge['to']],edge.get('to_port','l'),edge.get('to_offset',0))
    via=edge.get('via')
    if via is None:
        if abs(a[0]-b[0])<1e-8 or abs(a[1]-b[1])<1e-8: via=[]
        elif edge.get('from_port','r') in 'lr': via=[((a[0]+b[0])/2,a[1]),((a[0]+b[0])/2,b[1])]
        else: via=[(a[0],(a[1]+b[1])/2),(b[0],(a[1]+b[1])/2)]
    pts=[]
    for pt in [a]+list(via)+[b]:
        if len(pt)!=2 or not all(isinstance(v,(int,float)) and math.isfinite(v) for v in pt):
            raise ValueError('Invalid waypoint: '+edge['id'])
        pt=list(pt)
        if not pts or pt!=pts[-1]: pts.append(pt)
    for p,q in zip(pts,pts[1:]):
        if abs(p[0]-q[0])>1e-7 and abs(p[1]-q[1])>1e-7:
            raise ValueError('Nonorthogonal route: '+edge['id'])
    if len(pts)<2 or pts[0]==pts[-1]:
        raise ValueError('Connector needs distinct ports: '+edge['id'])
    routed=[pts[0]]; used=set()
    for p,q in zip(pts,pts[1:]):
        vertical=abs(p[0]-q[0])<1e-7
        axis=1 if vertical else 0
        candidates=[]
        for i,j in enumerate(edge.get('bridges',[])):
            x,y,r=j['x'],j['y'],j.get('radius',.14)
            if r<=0: raise ValueError('Bridge radius must be positive')
            center=y if vertical else x
            if abs((x if vertical else y)-p[1-axis])<1e-7 and min(p[axis],q[axis])+r<center<max(p[axis],q[axis])-r:
                candidates.append((center,i,x,y,r))
        candidates.sort(reverse=q[axis]<p[axis])
        for _,i,x,y,r in candidates:
            used.add(i)
            angles=[-math.pi/2+k*math.pi/16 for k in range(17)]
            arc=[(x+r*math.cos(t),y+r*math.sin(t)) if vertical else (x+r*math.sin(t),y-r*math.cos(t)) for t in angles]
            if q[axis]<p[axis]: arc.reverse()
            routed.extend(arc)
        routed.append(q)
    if len(used)!=len(edge.get('bridges',[])):
        raise ValueError('Bridge does not lie inside a clear segment: '+edge['id'])
    return pts,routed


def validate_spec(spec):
    if spec.get('version')!=1: raise ValueError('Expected spec version 1')
    for k in ('width','height'):
        if not 2<spec['page'][k]<=200: raise ValueError('Page dimension out of range')
    ids=set()
    for group in ('nodes','edges','regions','texts'):
        for item in spec.get(group,[]):
            key=item['id']
            if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*',key) or key in ids:
                raise ValueError('Invalid or duplicate ID: '+key)
            ids.add(key)
            if group in ('nodes','regions','texts'):
                for k in ('x','y'):
                    if not isinstance(item[k],(int,float)) or not math.isfinite(item[k]): raise ValueError('Invalid coordinate')
                if item.get('w',4.5)<=0 or item.get('h',.84)<=0: raise ValueError('Nonpositive shape size')
    nodes={n['id']:n for n in spec['nodes']}
    if not nodes: raise ValueError('At least one node required')
    for edge in spec['edges']:
        if edge['from'] not in nodes or edge['to'] not in nodes: raise ValueError('Unknown edge endpoint')
        route(edge,nodes)
    return nodes


def cell(s, key, value):
    s.CellsU(key).FormulaU=str(value)


class Renderer:
    def __init__(self, app, spec):
        self.app,self.spec=app,spec
        self.style={**STYLE,**spec.get('style',{})}
        self.palette={**PALETTE,**self.style.get('palette',{})}
        self.w,self.h=spec['page']['width'],spec['page']['height']
        self.doc=app.Documents.Add('');self.page=self.doc.Pages.Item(1)
        self.objects=[];self.nodes={};self.formulas={};self.edges=[];self.front=[];self.bridge_masks=[]
        for name in (self.style['font'],self.style['math_font']): self.doc.Fonts.Item(name)
        for k,v in dict(PageWidth=f'{self.w} in',PageHeight=f'{self.h} in',DrawingScale='1 in',PageScale='1 in',ShdwOffsetX=0,ShdwOffsetY=0).items(): cell(self.page.PageSheet,k,v)

    def color(self, value):
        value=self.palette.get(value,value)
        if not re.fullmatch(r'#[0-9A-Fa-f]{6}',value): raise ValueError('Unknown color '+str(value))
        return 'RGB('+','.join(str(int(value[i:i+2],16)) for i in (1,3,5))+')'

    def anchor(self,s,parent,dx,dy):
        cell(s,'PinX',f'GUARD(Sheet.{parent.ID}!PinX+{dx} in)')
        cell(s,'PinY',f'GUARD(Sheet.{parent.ID}!PinY-{dy} in)')

    def text(self,key,value,x,y,w,h,size=None,color='ink',bold=False,align=1,mathfont=True,fill=None,owner=None,kind='text',record=True):
        s=self.page.DrawRectangle(x-w/2,self.h-y-h/2,x+w/2,self.h-y+h/2);s.NameU=key
        plain,runs=markup(value);s.Text=plain
        cell(s,'LinePattern',0);cell(s,'FillPattern',1 if fill else 0)
        if fill: cell(s,'FillForegnd',self.color(fill))
        size=size or self.style['formula_pt']
        cell(s,'Char.Font',self.doc.Fonts.Item(self.style['math_font' if mathfont else 'font']).ID)
        cell(s,'Char.AsianFont',self.doc.Fonts.Item(self.style['font']).ID)
        for k,v in {'Char.Size':f'{size} pt','Char.Color':self.color(color),'Char.Style':1 if bold else 0,'Para.HorzAlign':align,'VerticalAlign':1,'Para.SpLine':f'{size*1.28} pt'}.items(): cell(s,k,v)
        for k in ('LeftMargin','RightMargin','TopMargin','BottomMargin'): cell(s,k,'.025 in')
        for a,b,pos in runs:
            chars=s.Characters;chars.Begin=a;chars.End=b;chars.CharProps(4,pos)
        if record:
            self.objects.append(dict(id=s.ID,name=key,kind=kind,owner=owner,text=plain,box=box(x,y,w,h)))
            self.front.append(s)
        return s

    def width(self, text, size):
        s=self.text('Measure',text,1,1,80,1,size=size,record=False)
        s.AddNamedRow(242,'Measure',0);cell(s,'User.Measure','TEXTWIDTH(TheText)')
        value=s.CellsU('User.Measure').ResultIU
        s.Delete();return value

    def rule(self,key,pts,parent,cx,cy,owner):
        # Horizontal endpoint frame keeps local geometry simple for math rules.
        left=min(x for x,y in pts);right=max(x for x,y in pts)
        s=self.page.DrawLine(left,self.h-cy,right,self.h-cy);s.NameU=key
        for r in range(s.RowCount(10)-1,0,-1): s.DeleteRow(10,r)
        for i,(x,y) in enumerate(pts):
            r=s.AddRow(10,-1,138 if i==0 else 139)
            s.CellsSRC(10,r,0).FormulaU=f'{x-left} in';s.CellsSRC(10,r,1).FormulaU=f'{cy-y} in'
        for k,v in {'LineColor':self.color('ink'),'LineWeight':'1.2 pt','BeginArrow':0,'EndArrow':0,'FillPattern':0}.items(): cell(s,k,v)
        self.anchor(s,parent,(left+right)/2-cx,cy-(self.h-parent.CellsU('PinY').ResultIU))
        self.front.append(s)
        return s

    def formula(self, n, parent):
        f=n['formula'];lines=[]
        if not f.get('lines'): raise ValueError('Formula needs at least one line: '+n['id'])
        for line in f['lines']:
            if isinstance(line,str): line={'text':line}
            if ('text' in line)==('parts' in line): raise ValueError('Formula line needs text XOR parts')
            size=line.get('size',self.style['formula_pt'])
            height=line.get('height',1.0 if 'parts' in line else .65)
            if height<=0: raise ValueError('Invalid formula line height')
            lines.append((line,size,height))
        width=f.get('width',n.get('w',4.5)+1.5);height=sum(q[2] for q in lines)
        top=n['y']+n.get('h',.84)/2+f.get('gap',.18);cy=top+height/2
        anchor=self.text('Formula_'+n['id'],'',n['x'],cy,width,height,record=False)
        self.anchor(anchor,parent,0,cy-n['y'])
        children=[];cursor=top
        for li,(line,size,lh) in enumerate(lines):
            yy=cursor+lh/2;cursor+=lh;key=f'Math_{n["id"]}_{li}'
            def add_text(suffix,value,x,y,w,h,pt):
                s=self.text(key+suffix,value,x,y,w,h,size=pt,color=line.get('color','ink'),owner=n['id'],kind='formula')
                self.anchor(s,anchor,x-n['x'],y-cy);children.append(s.ID)
            if 'text' in line:
                add_text('',line['text'],n['x'],yy,width,lh,size);continue
            measured=[]
            scale=size/29
            for part in line['parts']:
                if sum(k in part for k in ('text','fraction','sqrt'))!=1: raise ValueError('Invalid math part')
                if 'text' in part: pw=self.width(part['text'],size)
                elif 'sqrt' in part: pw=self.width(part['sqrt'],size)+.35*scale
                else:
                    if len(part['fraction'])!=2: raise ValueError('Fraction needs numerator/denominator')
                    pw=max(self.width(t,size*.86) for t in part['fraction'])+.12
                measured.append((part,pw,part.get('gap',.10)))
            total=sum(w+g for _,w,g in measured)-(measured[-1][2] if measured else 0)
            xx=n['x']-total/2
            for pi,(part,pw,gap) in enumerate(measured):
                pk=f'_{pi}'
                if 'text' in part: add_text(pk,part['text'],xx+pw/2,yy,pw+.03,lh,size)
                elif 'fraction' in part:
                    off=.235*size/28
                    if lh < 2*off+max(.48,size/72*1.4)-.001:
                        raise ValueError('Increase fraction line height: '+key)
                    for di,t in enumerate(part['fraction']): add_text(pk+str(di),t,xx+pw/2,yy+(-off if di==0 else off),pw,max(.48,size/72*1.4),size*.86)
                    s=self.rule(key+pk+'_bar',[(xx,yy),(xx+pw,yy)],anchor,n['x'],yy,n['id']);children.append(s.ID)
                else:
                    rw=.28*scale
                    add_text(pk,part['sqrt'],xx+rw+(pw-rw)/2,yy,pw-rw,lh,size)
                    pts=[(xx,yy+.04*scale),(xx+.075*scale,yy-.025*scale),(xx+.14*scale,yy+.18*scale),(xx+rw,yy-.235*scale),(xx+pw,yy-.235*scale)]
                    s=self.rule(key+pk+'_root',pts,anchor,n['x'],yy,n['id']);children.append(s.ID)
                xx+=pw+gap
        self.formulas[n['id']]=dict(id=anchor.ID,children=children,box=box(n['x'],cy,width,height))

    def node(self,n):
        x,y,w,h=n['x'],n['y'],n.get('w',4.5),n.get('h',.84)
        s=self.text('Node_'+n['id'],n['text'],x,y,w,h,size=self.style['node_pt'],bold=True,mathfont=False,owner=n['id'],kind='node')
        shape=n.get('shape','rect')
        if shape=='ellipse':
            # Ellipse geometry replaces the rectangle while preserving text formatting.
            original=s; s=self.page.DrawOval(x-w/2,self.h-y-h/2,x+w/2,self.h-y+h/2)
            s.NameU=original.NameU+'_oval';s.Text=original.Text
            for k in ('Char.Font','Char.AsianFont','Char.Size','Char.Style','Char.Color','Para.HorzAlign','VerticalAlign','Para.SpLine','LeftMargin','RightMargin','TopMargin','BottomMargin'): cell(s,k,original.CellsU(k).FormulaU)
            self.objects[-1]['id']=s.ID;self.objects[-1]['name']=s.NameU;self.front[-1]=s;original.Delete()
        elif shape=='diamond':
            for r in range(s.RowCount(10)-1,0,-1): s.DeleteRow(10,r)
            for i,(xx,yy) in enumerate([('Width/2','Height'),('Width','Height/2'),('Width/2','0'),('0','Height/2'),('Width/2','Height')]):
                r=s.AddRow(10,-1,138 if i==0 else 139);s.CellsSRC(10,r,0).FormulaU=xx;s.CellsSRC(10,r,1).FormulaU=yy
            cell(s,'TxtWidth','Width*0.65');cell(s,'TxtHeight','Height*0.65')
        elif shape!='rect': raise ValueError('Unsupported shape '+shape)
        color=n.get('color','green');fill=n.get('fill',color+'_fill' if color+'_fill' in self.palette else 'white')
        cell(s,'FillPattern',1);cell(s,'FillForegnd',self.color(fill));cell(s,'LinePattern',1);cell(s,'LineColor',self.color(color));cell(s,'LineWeight',f'{self.style["line_pt"]} pt')
        self.nodes[n['id']]=dict(id=s.ID,x=x,y=y,w=w,h=h)
        if n.get('formula'): self.formula(n,s)

    def edge(self,e):
        nodes={n['id']:n for n in self.spec['nodes']};base,pts=route(e,nodes);pa,pb=pts[0],pts[-1]
        s=self.page.DrawLine(pa[0],self.h-pa[1],pb[0],self.h-pb[1]);s.NameU='Edge_'+e['id']
        for cellname,key,point in [('BeginX',e['from'],pa),('EndX',e['to'],pb)]:
            n=self.nodes[key];target=self.page.Shapes.ItemFromID(n['id'])
            s.CellsU(cellname).GlueToPos(target,(point[0]-n['x']+n['w']/2)/n['w'],1-(point[1]-n['y']+n['h']/2)/n['h'])
        for r in range(s.RowCount(10)-1,0,-1): s.DeleteRow(10,r)
        for i,(x,y) in enumerate(pts):
            r=s.AddRow(10,-1,138 if i==0 else 139)
            if i==0: xx,yy='0','0'
            elif i==len(pts)-1: xx,yy='Width','0'
            else:
                xf='BeginX' if abs(x-pa[0])<1e-7 else ('EndX' if abs(x-pb[0])<1e-7 else f'{x} in')
                yf='BeginY' if abs(y-pa[1])<1e-7 else ('EndY' if abs(y-pb[1])<1e-7 else f'{self.h-y} in')
                xx=f'({xf}-BeginX)*COS(Angle)+({yf}-BeginY)*SIN(Angle)';yy=f'-({xf}-BeginX)*SIN(Angle)+({yf}-BeginY)*COS(Angle)'
            s.CellsSRC(10,r,0).FormulaU=xx;s.CellsSRC(10,r,1).FormulaU=yy
        for k,v in {'LineColor':self.color(e.get('color','green')),'LineWeight':f'{self.style["line_pt"]} pt','LinePattern':2 if e.get('dashed') else 1,'BeginArrow':0,'EndArrow':4 if e.get('arrow',True) else 0,'EndArrowSize':2,'FillPattern':0}.items(): cell(s,k,v)
        self.edges.append(dict(id=s.ID,key=e['id'],source=e['from'],target=e['to'],base=base,points=pts,bridges=e.get('bridges',[])))
        # Small native white masks at the detour peak keep crossed strokes apart.
        for j in e.get('bridges',[]):
            x,y,r=j['x'],j['y'],j.get('radius',.14)
            vertical=any(abs(a[0]-b[0])<1e-7 and abs(a[0]-x)<1e-7 and min(a[1],b[1])<y<max(a[1],b[1]) for a,b in zip(base,base[1:]))
            mx,my=(x+r,y) if vertical else (x,y-r)
            self.bridge_masks.append((mx,my,s))
        if e.get('label'):
            lab=e['label'];self.text('Label_'+e['id'],lab['text'],lab['x'],lab['y'],lab['w'],lab.get('h',.48),size=lab.get('size',self.style['note_pt']),color=e.get('color','green'),fill='white',owner=e['id'],kind='edge_label')

    def draw(self):
        bg=self.page.DrawRectangle(0,0,self.w,self.h);cell(bg,'LinePattern',0);cell(bg,'FillForegnd',self.color('white'))
        for r in self.spec.get('regions',[]):
            s=self.page.DrawRectangle(r['x']-r['w']/2,self.h-r['y']-r['h']/2,r['x']+r['w']/2,self.h-r['y']+r['h']/2)
            cell(s,'LineColor',self.color(r.get('color','rule')));cell(s,'FillForegnd',self.color(r.get('fill','white')));cell(s,'LineWeight','1 pt')
            if r.get('title'):
                tw=min(r['w']-.6,self.width(r['title'],28)+.3)
                self.text('Region_'+r['id'],r['title'],r['x']-r['w']/2+.3+tw/2,r['y']-r['h']/2+.5,tw,.7,size=28,color=r.get('color','ink'),bold=True,align=0,mathfont=False)
        if self.spec.get('title'): self.text('Title',self.spec['title'],self.w/2,.75,self.w-1.2,.9,size=self.style['title_pt'],bold=True,align=0,mathfont=False)
        for t in self.spec.get('texts',[]): self.text('Text_'+t['id'],t['text'],t['x'],t['y'],t['w'],t['h'],size=t.get('size',self.style['note_pt']),color=t.get('color','muted'),align=t.get('align',1),bold=t.get('bold',False),mathfont=t.get('math',True))
        for n in self.spec['nodes']: self.node(n)
        for e in self.spec['edges']: self.edge(e)
        for mx,my,edge in self.bridge_masks:
            m=self.page.DrawOval(mx-.08,self.h-my-.06,mx+.08,self.h-my+.06)
            cell(m,'LinePattern',0);cell(m,'FillForegnd',self.color('white'));edge.BringToFront()
        for j in self.spec.get('junctions',[]):
            x,y=j['x'],j['y'];s=self.page.DrawOval(x-.05,self.h-y-.05,x+.05,self.h-y+.05)
            cell(s,'LinePattern',0);cell(s,'FillForegnd',self.color(j.get('color','green')))
        for s in self.front: s.BringToFront()
        return dict(engine_version=1,spec=self.spec,objects=self.objects,nodes=self.nodes,formulas=self.formulas,edges=self.edges)


def geometry_audit(manifest):
    errors=[];warnings=[];objects=manifest['objects'];spec=manifest['spec'];w,h=spec['page']['width'],spec['page']['height']
    for o in objects:
        a=o['box']
        if a[0]<-.005 or a[1]<-.005 or a[2]>w+.005 or a[3]>h+.005: errors.append('Outside page: '+o['name'])
        if o['kind']=='formula':
            f=manifest['formulas'][o['owner']]['box']
            if a[0]<f[0]-.025 or a[1]<f[1]-.025 or a[2]>f[2]+.025 or a[3]>f[3]+.025:
                errors.append('Formula component exceeds its block: '+o['name'])
    for r in spec.get('regions',[]):
        a=box(r['x'],r['y'],r['w'],r['h'])
        if a[0]<0 or a[1]<0 or a[2]>w or a[3]>h: errors.append('Region outside page: '+r['id'])
    for i,a in enumerate(objects):
        for b in objects[i+1:]:
            if a.get('owner') and a.get('owner')==b.get('owner'): continue
            if overlap(a['box'],b['box']): errors.append('Overlap: '+a['name']+' / '+b['name'])
    for e in manifest['edges']:
        for o in objects:
            if o['kind']=='node' and o.get('owner') in (e['source'],e['target']): continue
            if o['kind']=='edge_label' and o.get('owner')==e['key']: continue
            if any(segment_hits(a,b,o['box']) for a,b in zip(e['points'],e['points'][1:])): errors.append('Route enters '+o['name']+': '+e['key'])
        if any(x<0 or x>w or y<0 or y>h for x,y in e['points']): errors.append('Route outside page: '+e['key'])
    for i,e in enumerate(manifest['edges']):
        for f in manifest['edges'][i+1:]:
            if {e['source'],e['target']} & {f['source'],f['target']}: continue
            for a,b in zip(e['base'],e['base'][1:]):
                for c,d in zip(f['base'],f['base'][1:]):
                    for u,v,s,t in ((a,b,c,d),(c,d,a,b)):
                        if abs(u[0]-v[0])<1e-8 and abs(s[1]-t[1])<1e-8:
                            x,y=u[0],s[1]
                            if min(u[1],v[1])+1e-6<y<max(u[1],v[1])-1e-6 and min(s[0],t[0])+1e-6<x<max(s[0],t[0])-1e-6:
                                marks=e['bridges']+f['bridges']+spec.get('junctions',[])
                                if not any(abs(j['x']-x)<.01 and abs(j['y']-y)<.01 for j in marks): warnings.append(f'Unmarked crossing: {e["key"]} / {f["key"]} at {x:g},{y:g}')
    return errors,sorted(set(warnings))


def audit(doc,manifest,vsdx):
    page=doc.Pages.Item(1);errors,warnings=geometry_audit(manifest);fits=[];moved=[]
    height=manifest['spec']['page']['height']
    for o in manifest['objects']:
        s=page.Shapes.ItemFromID(o['id'])
        if s.Text!=o['text']: errors.append('Text differs from manifest: '+o['name'])
        actual=box(s.CellsU('PinX').ResultIU,height-s.CellsU('PinY').ResultIU,s.CellsU('Width').ResultIU,s.CellsU('Height').ResultIU)
        if any(abs(a-b)>.005 for a,b in zip(actual,o['box'])): errors.append('Geometry differs from manifest: '+o['name'])
        for k,expr in [('TextHeight','TEXTHEIGHT(TheText,TxtWidth)'),('TextWidth','TEXTWIDTH(TheText)')]:
            if not s.CellExistsU('User.'+k,0): s.AddNamedRow(242,k,0)
            cell(s,'User.'+k,expr)
        th=s.CellsU('User.TextHeight').ResultIU;tw=s.CellsU('User.TextWidth').ResultIU
        ah=s.CellsU('TxtHeight').ResultIU;aw=s.CellsU('TxtWidth').ResultIU
        ok=th<=ah+.025 and ('\n' in s.Text or tw<=aw+.025)
        fits.append(dict(name=o['name'],height=ah,required_height=th,width=aw,required_width=tw,fits=ok))
        if not ok: errors.append('Text overflow: '+o['name'])
    for e in manifest['edges']:
        s=page.Shapes.ItemFromID(e['id']);conns=list(s.Connects)
        expected={manifest['nodes'][e[k]]['id'] for k in ('source','target')}
        if not s.OneD or len(conns)!=2 or {c.ToSheet.ID for c in conns}!=expected or {c.FromCell.Name for c in conns}!={'BeginX','EndX'}:
            errors.append('Connector is not glued at both ends: '+e['key'])
        if s.RowCount(10)-1 != len(e['points']):
            errors.append('Connector geometry row count differs: '+e['key'])
        else:
            bx=s.CellsU('BeginX').ResultIU;by=s.CellsU('BeginY').ResultIU;angle=s.CellsU('Angle').ResultIU
            for row,(px,py) in enumerate(e['points'],1):
                xx=s.CellsSRC(10,row,0).ResultIU;yy=s.CellsSRC(10,row,1).ResultIU
                ax=bx+xx*math.cos(angle)-yy*math.sin(angle)
                ay=height-(by+xx*math.sin(angle)+yy*math.cos(angle))
                if abs(ax-px)>1e-5 or abs(ay-py)>1e-5:
                    errors.append('Saved connector route differs: '+e['key']);break
    for key,f in manifest['formulas'].items():
        node=page.Shapes.ItemFromID(manifest['nodes'][key]['id']);anchor=page.Shapes.ItemFromID(f['id'])
        if anchor.CellsU('PinY').ResultIU+anchor.CellsU('Height').ResultIU/2>=node.CellsU('PinY').ResultIU-node.CellsU('Height').ResultIU/2:
            errors.append('Formula not below node: '+key)
        refs=(f'Sheet.{node.ID}!'.lower(),(node.NameU+'!').lower())
        if not all(any(ref in anchor.CellsU(c).FormulaU.lower() for ref in refs) for c in ('PinX','PinY')):
            errors.append('Formula anchor not associated: '+key)
    # Exercise every node without saving, including all math components and edges.
    for key,n in manifest['nodes'].items():
        node=page.Shapes.ItemFromID(n['id']);x=node.CellsU('PinX').ResultIU;y=node.CellsU('PinY').ResultIU
        targets=[]
        if key in manifest['formulas']:
            f=manifest['formulas'][key]
            for sid in [f['id']]+f['children']:
                s=page.Shapes.ItemFromID(sid);targets.extend([(s,'PinX',s.CellsU('PinX').ResultIU,.23),(s,'PinY',s.CellsU('PinY').ResultIU,.17)])
        for e in manifest['edges']:
            for end,field in [('Begin','source'),('End','target')]:
                if e[field]==key:
                    s=page.Shapes.ItemFromID(e['id']);targets.extend([(s,end+'X',s.CellsU(end+'X').ResultIU,.23),(s,end+'Y',s.CellsU(end+'Y').ResultIU,.17)])
        node.CellsU('PinX').ResultIU=x+.23;node.CellsU('PinY').ResultIU=y+.17
        ok=all(abs(s.CellsU(c).ResultIU-v-delta)<1e-5 for s,c,v,delta in targets)
        node.CellsU('PinX').ResultIU=x;node.CellsU('PinY').ResultIU=y
        moved.append(dict(node=key,passed=ok))
        if not ok: errors.append('Components/endpoints do not follow moved node: '+key)
    with zipfile.ZipFile(vsdx) as z:
        if any(n.startswith('visio/media/') for n in z.namelist()) or b'<ForeignData' in z.read('visio/pages/page1.xml'): errors.append('Embedded raster or foreign object')
    return dict(reopened=True,errors=sorted(set(errors)),warnings=warnings,text_checks=fits,movement_checks=moved,native_nodes=len(manifest['nodes']),glued_flow_connectors=len(manifest['edges']),visual_review='REQUIRED: inspect the exported PNG separately')


def application():
    if sys.platform!='win32': raise RuntimeError('Run with Windows Python and installed desktop Visio')
    import win32com.client
    app=win32com.client.DispatchEx('Visio.InvisibleApp');app.AlertResponse=7
    return app


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('probe')
    p=sub.add_parser('render');p.add_argument('spec');p.add_argument('--output',required=True);p.add_argument('--overwrite',action='store_true')
    p=sub.add_parser('verify');p.add_argument('vsdx');p.add_argument('--manifest',required=True)
    args=parser.parse_args();app=None;doc=None
    try:
        if args.command=='probe':
            app=application();doc=app.Documents.Add('')
            fonts={name:doc.Fonts.Item(name).ID for name in (STYLE['font'],STYLE['math_font'])}
            print(json.dumps(dict(python=sys.executable,visio_version=app.Version,fonts=fonts),ensure_ascii=False));return 0
        if args.command=='render':
            spec=read_json(args.spec);validate_spec(spec);dest=Path(args.output).resolve()
            if dest.suffix.lower()!='.vsdx': raise ValueError('Output must end in .vsdx')
            paths=[dest,dest.with_suffix('.png'),dest.with_suffix('.manifest.json'),dest.with_suffix('.audit.json')]
            if not args.overwrite and any(p.exists() for p in paths): raise FileExistsError('Choose a new output stem or explicitly pass --overwrite')
            dest.parent.mkdir(parents=True,exist_ok=True)
            app=application();renderer=Renderer(app,spec);doc=renderer.doc
            manifest=renderer.draw();doc.SaveAs(str(dest));doc.Close();doc=None
            manifest['source_spec_sha256']=sha(args.spec);manifest['vsdx_sha256']=sha(dest)
            write_json(dest.with_suffix('.manifest.json'),manifest)
            doc=app.Documents.OpenEx(str(dest),64+128)
            dpi=spec.get('export',{}).get('dpi',120)
            app.Settings.SetRasterExportResolution(3,dpi,dpi,0)
            app.Settings.SetRasterExportSize(2,round(spec['page']['width']*dpi),round(spec['page']['height']*dpi),0)
            png=dest.with_suffix('.png');doc.Pages.Item(1).Export(str(png))
            report=audit(doc,manifest,dest)
            with png.open('rb') as stream:
                header=stream.read(24)
            dims=struct.unpack('>II',header[16:24]);expected=(round(spec['page']['width']*dpi),round(spec['page']['height']*dpi))
            if header[:8]!=b'\x89PNG\r\n\x1a\n' or dims!=expected: report['errors'].append('PNG size/signature mismatch')
            report['png_pixels']=dims
            report['files']={p.name:dict(bytes=p.stat().st_size,sha256=sha(p)) for p in (dest,png)}
        else:
            dest=Path(args.vsdx).resolve();manifest=read_json(args.manifest);app=application();doc=app.Documents.OpenEx(str(dest),64+128)
            report=audit(doc,manifest,dest)
            if manifest.get('vsdx_sha256')!=sha(dest): report['errors'].append('VSDX changed since manifest: inspect and preserve manual edits')
        write_json(dest.with_suffix('.audit.json'),report)
        print(json.dumps(dict(vsdx=str(dest),nodes=report['native_nodes'],connectors=report['glued_flow_connectors'],errors=report['errors'],warnings=report['warnings']),ensure_ascii=False))
        return 2 if report['errors'] else 0
    finally:
        if doc is not None:
            try: doc.Saved=True;doc.Close()
            except Exception: pass
        if app is not None: app.Quit()


if __name__=='__main__':
    if hasattr(sys.stdout,'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    try: sys.exit(main())
    except Exception as exc:
        print(f'{type(exc).__name__}: {exc}',file=sys.stderr);sys.exit(1)
