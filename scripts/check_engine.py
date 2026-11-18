"""Exercise validation against rendered examples; mutations are never saved."""
import argparse
import copy
import json
import sys
from pathlib import Path
from render import application, audit, read_json, write_json, geometry_audit, markup, validate_spec, Renderer, sha


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('example_output_dir',help='Directory containing the three rendered bundled examples')
    args=p.parse_args();out=Path(args.example_output_dir).resolve()
    report={'positive':{},'negative':{},'pure_checks':{}}
    app=application();doc=None
    try:
        for name in ('branch-fusion','skip-network','layered-system'):
            path=out/(name+'.vsdx');manifest=read_json(path.with_suffix('.manifest.json'))
            original_hash=sha(path)
            doc=app.Documents.OpenEx(str(path),64+128)
            result=audit(doc,manifest,path)
            assert not result['errors'],result['errors']
            assert not result['warnings'],result['warnings']
            report['positive'][name]={'nodes':result['native_nodes'],'connectors':result['glued_flow_connectors'],'passed':True}
            if name=='branch-fusion':
                m=copy.deepcopy(manifest)
                a=next(o for o in m['objects'] if o['name']=='Node_input')
                b=next(o for o in m['objects'] if o['name']=='Node_bright')
                b['box']=a['box'][:]
                errors,_=geometry_audit(m)
                assert any('Overlap:' in e for e in errors)
                report['negative']['overlap_detected']=True
                # Oversized native text should fail fit, even with the original string.
                node=doc.Pages.Item(1).Shapes.ItemFromID(manifest['nodes']['input']['id'])
                old=node.CellsU('Char.Size').FormulaU;node.CellsU('Char.Size').FormulaU='300 pt'
                bad=audit(doc,manifest,path)
                assert 'Text overflow: Node_input' in bad['errors'],bad['errors']
                report['negative']['native_text_overflow_detected']=True
                node.CellsU('Char.Size').FormulaU=old
                # Replacing an endpoint glue formula with a constant disconnects it.
                edge=doc.Pages.Item(1).Shapes.ItemFromID(manifest['edges'][0]['id'])
                edge.CellsU('BeginX').FormulaU=f'{edge.CellsU("BeginX").ResultIU} in'
                bad=audit(doc,manifest,path)
                assert any('not glued at both ends' in e for e in bad['errors']),bad['errors']
                report['negative']['detached_connector_detected']=True
            doc.Saved=True;doc.Close();doc=None
            assert sha(path)==original_hash
        # Exercise the third supported primitive without adding another packaged layout.
        spec={'version':1,'page':{'width':14,'height':8},'title':'原生菱形检查',
              'nodes':[{'id':'decision','text':'判断','x':4,'y':3.5,'w':4,'h':2,'shape':'diamond','formula':{'width':4,'lines':['x > 0']}},
                       {'id':'done','text':'输出','x':10,'y':3.5,'w':3.5,'h':1.2,'shape':'ellipse'},
                       {'id':'root','text':'','x':10,'y':5.6,'w':3.,'h':.74,
                        'formula':{'placement':'inside','lines':[{'parts':[{'text':'1 −'},{'sqrt':'1 − x'}],'height':.62}]}}],
              'edges':[{'id':'yes','from':'decision','to':'done','label':{'text':'是','x':7.1,'y':3.5,'w':.8}},
                       {'id':'root_input','from':'done','to':'root','from_port':'b','to_port':'t'}]}
        renderer=Renderer(app,spec);doc=renderer.doc;manifest=renderer.draw()
        path=out/'shape-check.vsdx';doc.SaveAs(str(path));doc.Close();doc=None
        doc=app.Documents.OpenEx(str(path),64+128)
        original_hash=sha(path)
        result=audit(doc,manifest,path);assert not result['errors'],result['errors']
        report['positive']['diamond_and_ellipse']={'passed':True}
        write_json(path.with_suffix('.audit.json'),result)
        report['positive']['inline_radical']={'passed':True}
        root=manifest['formulas']['root']['roots'][0]
        rule=doc.Pages.Item(1).Shapes.ItemFromID(root['rule'])
        rule.DeleteRow(10,rule.RowCount(10)-1)
        bad=audit(doc,manifest,path)
        assert 'Radical geometry is incomplete: root' in bad['errors'],bad['errors']
        report['negative']['missing_radical_bar_detected']=True
        doc.Saved=True;doc.Close();doc=None
        assert sha(path)==original_hash
    finally:
        if doc is not None: doc.Saved=True;doc.Close()
        app.Quit()
    plain,runs=markup('😀 X_{i} + y^{2}')
    assert plain=='😀 Xi + y2' and runs==[(4,5,2),(9,10,1)],(plain,runs)
    report['pure_checks']['utf16_math_spans']=True
    try: markup('x_{a_{b}}')
    except ValueError: report['negative']['nested_markup_rejected']=True
    else: raise AssertionError('Nested markup silently accepted')
    broken=read_json(Path(__file__).resolve().parents[1]/'assets/examples/branch-fusion.json')
    broken['edges'][0]['to']='missing'
    try: validate_spec(broken)
    except ValueError: report['negative']['missing_endpoint_rejected']=True
    else: raise AssertionError('Missing endpoint accepted')
    write_json(out/'engine-test-report.json',report)
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':
    if hasattr(sys.stdout,'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    main()
