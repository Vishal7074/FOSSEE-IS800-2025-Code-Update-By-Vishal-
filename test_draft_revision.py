"""Independent examples for the revised original module. Units are N, mm and MPa."""
import math
import unittest
from steel.utils.common.is800_2007 import IS800_2025_Draft as D
from is800_2025_draft import IS800_2025_Draft as RootDraft


class RevisionExamples(unittest.TestCase):
    def test_project_entry(self):
        self.assertIs(RootDraft, D)
        self.assertEqual(D.Table2_iii(750, 10, 250), "Compact")

    def test_yielding_original_entry(self):
        self.assertAlmostEqual(D.cl_6_2_tension_yielding_strength(1100, 250), 250000)

    def test_thermal_contraction(self):
        self.assertAlmostEqual(D.thermal_movement(10000, -40), -4.8)

    def test_fire_occupancies_and_restraint(self):
        self.assertEqual(D.fire_load_effect(100, 60, -10, storage=True), 150)
        self.assertEqual(D.fire_load_effect(100, 60, -10, storage=False), 120)

    def test_fire_yield(self):
        for temp, strength in [(20, 250), (215, 250), (560, 125), (905, 0)]:
            self.assertEqual(D.fire_yield_strength(250, temp), strength)

    def test_fire_stiffness(self):
        self.assertAlmostEqual(D.fire_modulus_ratio(600), 0.50506, places=4)
        self.assertAlmostEqual(D.fire_modulus_ratio(700), 207/646.5)
        self.assertEqual(D.fire_modulus_ratio(1000), 0)

    def test_stability_route_boundaries(self):
        for case, lower, upper in [(True, 4.6, 10), (False, 5.75, 20)]:
            for factor, route in [(lower-.01, 'second-order'), (lower, 'amplification-permitted'),
                                  (upper-.01, 'amplification-permitted'), (upper, 'first-order')]:
                self.assertEqual(D.frame_analysis_route(2*factor, 2, clad_without_infill_stiffness=case), route)

    def test_elastic_amplification_limit(self):
        self.assertTrue(D.elastic_amplification_allowed(1.4, 1))
        self.assertFalse(D.elastic_amplification_allowed(1, 1.401))

    def test_seismic_route(self):
        self.assertEqual(D.seismic_frame_route('II', 'normal'), 'ordinary-permitted')
        self.assertEqual(D.seismic_frame_route('III', 'normal'), 'special-required')
        with self.assertRaises(NotImplementedError):
            D.seismic_frame_route('II', 'important')

    def test_built_up_brace(self):
        checks = D.ocbf_brace_checks('Compact', 120, 800, 1000, 850, 900, built_up=True,
                                     component_slenderness=48, central_bolts=True)
        self.assertEqual([key for key, ok in checks.items() if not ok], ['central_quarter'])

    def test_brace_connections(self):
        for combination, transfer, governing in [(500000, 600000, 300000), (200000, 600000, 200000),
                                                 (200000, 125000, 125000)]:
            self.assertEqual(D.brace_connection_actions(250, 1000, combination, transfer, 2000),
                             (governing, 2400))

    def test_anchor_steel_and_group_ductility(self):
        self.assertEqual(D.anchor_steel(100, 640, 800, group=False, elongation_percent=7)[1], 32000)
        t, v = D.anchor_steel(100, 640, 800, group=True, elongation_percent=7)
        self.assertAlmostEqual(t, 80000/1.5)
        self.assertEqual(v, 25600)
        self.assertEqual(D.anchor_steel(100, 810, 900, group=True, elongation_percent=8)[1], 30000)

    def test_pullout(self):
        self.assertAlmostEqual(D.anchor_pullout(100, 25, cracked=False), 22400)
        with self.assertRaises(ValueError):
            D.anchor_pullout(100, 55, cracked=True)

    def test_pyramid_group(self):
        capacity = D.anchor_pyramid(25, 100, 20000, 10000, edge=.8, spalling=1, eccentricity=.5, cracking=1)
        self.assertAlmostEqual(capacity, 28800/2.15)

    def test_pryout_embedment_boundary(self):
        self.assertEqual(D.anchor_pryout(59.9, 1000), 1000)
        self.assertEqual(D.anchor_pryout(60, 1000), 2000)

    def test_anchor_splitting_depth(self):
        self.assertEqual(D.anchor_splitting(1000, 200, 100), 1000)
        self.assertEqual(D.anchor_splitting(1000, 600, 100), 1500)

    def test_anchor_bending(self):
        self.assertEqual(D.anchor_shear_with_bending(10000, 500, 1000, 100, 500, 20, 1.5, fixed=False), 1000)
        self.assertEqual(D.anchor_shear_with_bending(10000, 1000, 1000, 100, 500, 20, 1.5, fixed=True), 0)

    def test_anchor_edge(self):
        capacity = D.anchor_edge_shear(25, 25, 100, 25, 1000, 1000, corner=1, direction=1,
                                       eccentricity=1, cracking=1, depth=1)
        self.assertAlmostEqual(capacity, 6250)

    def test_anchor_interaction(self):
        self.assertAlmostEqual(D.anchor_interaction(60, 80, 100, 100, both_steel=True), 1)
        self.assertGreater(D.anchor_interaction(60, 80, 100, 100, both_steel=False), 1)

    def test_corrugated_flange(self):
        self.assertAlmostEqual(D.corrugated_moment(500, 100, 10, 200, 12, 200, 250), 200000*511/1.1)

    def test_corrugated_interaction(self):
        self.assertAlmostEqual(D.corrugated_shear(100, 2, math.sqrt(3)*100, 1000, 1000),
                               20000/math.sqrt(2)/1.1)

    def test_corrugation_profiles(self):
        common = (100, 2, 192000, 0, 20, 100)
        for profile, kwargs, multiplier, divisor in [
                ('profiled', dict(panel_width=50), 6.675, 2500),
                ('profiled', dict(panel_width=150), 11.35, 2500),
                ('sinusoidal', dict(wave_depth=10), 7.35, 400)]:
            local, overall = D.corrugated_critical_stresses(*common, profile=profile,
                                                            developed_length=40, **kwargs)
            self.assertAlmostEqual(local, multiplier*math.pi**2*16000/divisor)
            self.assertAlmostEqual(overall, 32.4*(64000*960000**3)**.25/20000)

    def test_bearing_at_end(self):
        self.assertEqual(D.stiff_bearing_length(50, 20, 0, 10), 60)
        self.assertAlmostEqual(D.local_web_bearing(60, 50, 10, 250), 250000)

    def test_fatigue_stress_reversal(self):
        checks = D.fatigue_constant_range(-200, 200, 250, 100, 1, 1.25, stress='normal')
        self.assertEqual(checks, dict(elastic=True, range_limit=False, fatigue=False))

    def test_lifecycle_signed_inventory(self):
        self.assertEqual(D.lifecycle_emissions(manufacturing=100, transport=12, fabrication=8,
                          erection=3, finishing=6, commissioning=1, maintenance=10, end_of_life=-5), 135)

    def test_flange_transverse_bending(self):
        self.assertEqual(D.corrugated_flange_stresses(250, 300, 100, 10, 0, 0, 1000, 175),
                         (175, 300))
        with self.assertRaises(ValueError):
            D.corrugated_flange_stresses(250, 300, 100, 10, 0, 1000, 1000, 175)

    def test_earthquake_anchor_threshold(self):
        self.assertEqual(D.seismic_anchor_route(20, 100), 'G-2')
        self.assertEqual(D.seismic_anchor_route(21, 100), 'G-3')
