"""Actual dated observations and comparison/official separation regressions."""
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from gokpop_public.content import J_EXACT, load_content
from gokpop_public.history import chart_spec, load_history, prepare_history


class LectureHistoryTests(unittest.TestCase):
    def setUp(self):
        self.content = load_content(ROOT)
        self.payload = json.loads((ROOT / 'data/public/lecture_history.json').read_text(encoding='utf-8'))

    def test_seven_actual_observations_and_irregular_date_intervals(self):
        rows = prepare_history(self.payload, self.content)
        self.assertEqual([(r['date'], r['views'], r['likes']) for r in rows], [
            ('2026-10-18', 55396, 1652), ('2026-10-21', 62356, 1848),
            ('2026-10-25', 65545, 1863), ('2026-10-27', 68320, 1868),
            ('2026-10-28', 70238, 1871), ('2026-10-29', 74697, 1888),
            ('2026-10-31', 76716, 1901),
        ])
        self.assertEqual([r['days_from_baseline'] for r in rows], [0, 3, 7, 9, 10, 11, 13])

    def test_exact_scores_preserve_official_edition_and_both_inputs(self):
        before_payload, before_content = deepcopy(self.payload), deepcopy(self.content)
        before_bytes = (ROOT / 'data/public/site_data.json').read_bytes()
        rows = prepare_history(self.payload, self.content)
        self.assertEqual(rows[0]['I1_exact'], Fraction('8930840/2600709'))
        self.assertEqual(rows[-1]['I1_exact'], Fraction('889902790/221938029'))
        self.assertEqual(rows[0]['J_comparison_exact'], Fraction(J_EXACT))
        self.assertAlmostEqual(float(rows[-1]['J_comparison_exact']), 70.01226211403491, places=12)
        self.assertEqual([r['J_official_exact'] for r in rows], [Fraction(J_EXACT)] + [None] * 6)
        for row in rows:
            self.assertEqual(row['J_comparison_exact'] - Fraction(J_EXACT), row['I1_change'])
        self.assertEqual(self.payload, before_payload)
        self.assertEqual(self.content, before_content)
        self.assertEqual((ROOT / 'data/public/site_data.json').read_bytes(), before_bytes)
        self.assertEqual(len(self.content['records']), 1)

    def test_missing_wrong_type_and_negative_counts_are_rejected(self):
        for field, value in [('views', -1), ('likes', True), ('views', 62356.0), ('likes', '1848')]:
            with self.subTest(field=field, value=value):
                payload = deepcopy(self.payload)
                payload['observations'][0][field] = value
                with self.assertRaises(ValueError):
                    prepare_history(payload, self.content)
        payload = deepcopy(self.payload)
        del payload['observations'][0]['likes']
        with self.assertRaises(ValueError):
            prepare_history(payload, self.content)

    def test_duplicate_publication_and_invalid_dates_are_rejected(self):
        for value in ['2026-10-14', '2026-10-18', '2026-10-25', '2026-10-32', '2026-1021', '20261021']:
            with self.subTest(value=value):
                payload = deepcopy(self.payload)
                payload['observations'][0]['date'] = value
                with self.assertRaises(ValueError):
                    prepare_history(payload, self.content)

    def test_mismatched_video_formula_and_private_fields_are_rejected(self):
        for field, value in [('video_url', 'https://www.youtube.com/watch?v=other'),
                             ('formula_version', 'another-formula'), ('raw_comments', ['private'])]:
            with self.subTest(field=field):
                payload = deepcopy(self.payload)
                payload[field] = value
                with self.assertRaises(ValueError):
                    prepare_history(payload, self.content)

    def test_declining_counts_remain_real_observations(self):
        payload = deepcopy(self.payload)
        payload['observations'][-1].update(views=74000, likes=1800)
        rows = prepare_history(payload, self.content)
        self.assertEqual((rows[-1]['views'], rows[-1]['likes']), (74000, 1800))
        self.assertLess(rows[-1]['I1_exact'], rows[-2]['I1_exact'])

    def test_chart_preserves_dates_and_comparison_is_labelled(self):
        rows = load_history(ROOT, self.content)
        for metric in ['조회수', '좋아요', '강의 영상 점수', '종합지수 비교']:
            spec = chart_spec(rows, metric, zoom=False)
            self.assertEqual(len(spec['data']['values']), 7)
            self.assertEqual(spec['encoding']['x']['type'], 'temporal')
            self.assertEqual(spec['encoding']['x']['scale']['type'], 'utc')
            self.assertEqual([r['date'] for r in spec['data']['values']], [r['date'] for r in rows])
            self.assertEqual(spec['encoding']['tooltip'][0]['field'], 'observation_date')
            self.assertEqual([r['observation_date'] for r in spec['data']['values']], [r['date'] for r in rows])
        comparison = chart_spec(rows, '종합지수 비교', zoom=False)
        self.assertIn('비교', comparison['encoding']['y']['title'])
        self.assertEqual(comparison['encoding']['y']['scale']['domain'], [0, 100])
        self.assertIn('strokeDash', comparison['mark'])
        self.assertEqual(chart_spec(rows, '강의 영상 점수', False)['encoding']['y']['scale']['domain'], [0, 10])


if __name__ == '__main__':
    unittest.main()
