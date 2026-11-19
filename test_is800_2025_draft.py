"""Focused checks for the study migration. Run python -m unittest -v."""
import math
import unittest
from is800_2025_draft import IS800_2025_Draft as D


class DraftRules(unittest.TestCase):
    def test_web(self):
        for loading, limits in [('mid-depth',(70,80,120)),('axial',(32,36.8,40.7))]:
            for i,value in enumerate(limits):
                labels = ['Plastic','Compact','Semi-Compact','Slender']
                self.assertEqual(D.web_class(value,1,250,loading=loading),labels[i])
                self.assertEqual(D.web_class(value+.001,1,250,loading=loading),labels[i+1])
        self.assertEqual(D.web_general_limit(250,.4,section_class='Plastic'),87.5)
        self.assertEqual(D.web_general_limit(250,1,section_class='Plastic'),32)

    def test_flange_and_angles(self):
        self.assertEqual(D.outstand_class(90,10,250),'Compact')
        self.assertEqual(D.outstand_class(17.4,1,250,stress='tip-compression',compression_fraction=.5),'Plastic')
        with self.assertRaises(NotImplementedError):
            D.outstand_class(22,1,250,stress='tip-compression',compression_fraction=.5)
        self.assertEqual(D.angle_class(12,12,1,250,case='separated-axial'),'Slender')
        self.assertEqual(D.angle_class(20,9,1,250,case='contact-leg'),'Compact')

    def test_tube(self):
        for fy in (250,500):
            for limit,cls in [(47,'Plastic'),(66,'Compact'),(85,'Semi-Compact'),(85.1,'Slender')]:
                self.assertEqual(D.tube_class(limit*250/fy,1,fy,loading='moment'),cls)
        self.assertEqual(D.tube_class(86,1,250,loading='axial'),'Semi-Compact')
        self.assertEqual(D.tube_class(87,1,250,loading='axial'),'Slender')

    def test_materials(self):
        self.assertEqual([D.steel_strength('E350',t)[0] for t in (19,20,40,41)],[350,330,330,320])
        self.assertEqual(D.specialty_fy('WR-Fe480B',45),340)
        with self.assertRaises(NotImplementedError):
            D.specialty_fy('FR-Fe410',25)

    def test_column(self):
        self.assertEqual([D.maximum_slenderness(i) for i in range(1,7)],[180,180,250,300,350,400])
        self.assertIsNone(D.maximum_slenderness(6,sag_avoided=True))
        self.assertEqual(D.buckling_curves('rolled-I',420,h=300,b=150,tf=40),('a','b'))
        self.assertEqual(D.buckling_curves('rolled-I',421,h=300,b=150,tf=40),('a0','a'))
        with self.assertRaises(NotImplementedError):
            D.buckling_curves('welded-I',250,tf=40)
        self.assertEqual(D.column_table('a0',10,250)[1],227)
        self.assertEqual(D.column_table('c',100,250)[1],107)
        with self.assertRaises(ValueError):
            D.column_table('c',101,250)
        self.assertEqual(D.effective_length(4000,'pinned','fixed'),3200)

    def test_base_and_moments(self):
        self.assertEqual([D.bearing_pressure(30,25,r,1) for r in (1,4,9)],[11.25,22.5,22.5])
        self.assertAlmostEqual(D.low_shear_moment('Semi-Compact',1200,1000,250,'simply-supported'),250000/1.1)
        self.assertFalse(D.beam_high_shear(60,100))
        self.assertAlmostEqual(D.high_shear_moment('Compact',100,40,10,250,75,100),85)
        self.assertEqual(D.ltb_moment('Slender',1200,1000,200,zeff=700),140000)
        self.assertAlmostEqual(D.gradient_factor(2,1),1)
        self.assertAlmostEqual(D.ltb_reduction(1,1,.2,1)[0],1.08)
        self.assertEqual(D.simple_beam_ltb_length(1,1000,200,loading='normal'),700)

    def test_shear(self):
        self.assertFalse(D.web_shear_buckling_required(670,10,250))
        self.assertTrue(D.web_shear_buckling_required(671,10,250))
        self.assertFalse(D.web_thickness_ok(100,1,250,250,stiffening='none',edges=1))
        self.assertTrue(D.web_thickness_ok(100,1,250,250,stiffening='none',edges=2))
        self.assertAlmostEqual(D.postcritical_shear(100,10,250,200000,.3),250/math.sqrt(3))
        self.assertEqual(D.tension_field(500,500,5,250,2500,80,201000,(200,20,250,0),(200,20,250,0)),201000)

    def test_connections(self):
        self.assertEqual(D.hole_dimensions(20,'long-slot'),(22,70))
        for direction,kh in [('long-parallel',.7),('long-perpendicular',.85)]:
            load,actual,gamma=D.slip_resistance(800,245,2,.3,hole=direction,load_level='ultimate')
            self.assertEqual(actual,kh)
            self.assertAlmostEqual(load,.3*2*kh*.7*800*245/1.25)
        with self.assertRaises(ValueError):
            D.bolt_grip_factor(20,161)
        self.assertEqual(D.min_weld_size(40,20,first_run=True),8)
        self.assertEqual(D.min_weld_size(40,20),10)
        self.assertEqual(D.weld_throat(5,90),3.5)
        with self.assertRaises(ValueError):
            D.weld_throat(4,90)
        self.assertEqual(D.fillet_effective_length(6,24),12)
        self.assertAlmostEqual(D.weld_long_joint(600*5,5),.4)

if __name__ == '__main__':
    unittest.main()
