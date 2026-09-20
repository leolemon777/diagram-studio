import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from render import build, audit, drawio, render_file


class StoryMapTests(unittest.TestCase):
    def setUp(self):
        self.data=json.loads((ROOT/'assets/storymap-examples/education-storymap.json').read_text())

    def test_complete_assignments_and_editable_source(self):
        scene=build(self.data,'light')
        self.assertFalse(audit(scene)['errors'])
        assignment=scene.meta['story_map']['assignments']
        self.assertEqual({(x['id'],x['activity'],x['release']) for x in self.data['stories']},
                         {(x['story'],x['activity'],x['release']) for x in assignment})
        ids={c.get('id') for c in ET.fromstring(drawio(scene)).iter('mxCell')}
        for story in self.data['stories']:
            self.assertIn('story-'+story['id'],ids)
            self.assertTrue(any(n['label']==story['detail'] for n in scene.nodes))
        self.assertTrue(any(n['label']=='— 未安排' for n in scene.nodes))
        self.assertFalse(scene.meta['story_map']['calendar_scale'])

    def test_long_content_expands_row_without_changing_font(self):
        initial=build(self.data,'light')
        self.data['stories'][0]['detail']+='\n很长的中文解释，用来验证内容增长后仍然完整显示。'*24
        updated=build(self.data,'light')
        before=initial.meta['story_map']['releases']
        after=updated.meta['story_map']['releases']
        self.assertGreater(after[0]['height'],before[0]['height'])
        self.assertGreater(after[1]['y'],before[1]['y'])
        self.assertFalse(audit(updated)['errors'])
        self.assertEqual(updated.get('storytext-S01-2')['fs'],17)
        for a in updated.meta['story_map']['assignments']:
            row=next(r for r in after if r['release']==a['release'])
            self.assertLessEqual(a['box'][1]+a['box'][3],row['y']+row['height'])

    def test_reordering_activities_preserves_story_ownership(self):
        a=build(self.data,'light')
        self.data['activities'].reverse()
        b=build(self.data,'light')
        self.assertGreater(b.get('story-S01')['x'],a.get('story-S01')['x'])
        self.assertLess(b.get('story-S03')['x'],a.get('story-S03')['x'])
        self.assertFalse(audit(b)['errors'])

    def test_rejects_semantic_ambiguity(self):
        changes=[lambda d:d['stories'].append(copy.deepcopy(d['stories'][0])),
                 lambda d:d['stories'][0].update(activity='missing'),
                 lambda d:d['stories'][0].update(release='missing'),
                 lambda d:d['releases'][0].update(goal=''),
                 lambda d:d.update(dependencies=[]),
                 lambda d:d['stories'][0].update(votes=12)]
        for change in changes:
            d=copy.deepcopy(self.data);change(d)
            with self.subTest(data=d),self.assertRaises(ValueError):build(d,'light')

    def test_failed_update_preserves_last_delivery(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'map.json';out=Path(folder)/'out'
            path.write_text(json.dumps(self.data));render_file(path,out)
            before={p.name:p.read_bytes() for p in out.iterdir()}
            self.data['stories'][0]['release']='unknown'
            path.write_text(json.dumps(self.data))
            with self.assertRaises(ValueError):render_file(path,out)
            self.assertEqual(before,{p.name:p.read_bytes() for p in out.iterdir()})

    def test_english_long_title_and_single_activity(self):
        d=json.loads((ROOT/'assets/storymap-examples/education-storymap-en.json').read_text())
        d['activities']=d['activities'][:1]
        d['stories']=[x for x in d['stories'] if x['activity']=='discover']
        d['activities'][0]['label']='Understand the full course experience before making a commitment'
        d['activities'][0]['id']='activity_'+'a'*55
        for story in d['stories']:
            story['activity']=d['activities'][0]['id']
        self.assertFalse(audit(build(d,'mono'))['errors'])

if __name__=='__main__':unittest.main()
