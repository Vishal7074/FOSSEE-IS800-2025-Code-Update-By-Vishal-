"""Module for Indian Standard, IS 800 : 2007

Started on 01 - Nov - 2018

@author: ajmalbabums
"""
import math
from ...Common import *
import pandas as pd
# from ...Common import KEY_DP_FAB_SHOP


class IS800_2007(object):
    """Perform calculations on steel design as per IS 800:2007

    """

    # ==========================================================================
    """    SECTION  1     GENERAL   """
    # ==========================================================================
    """    SECTION  2     MATERIALS   """
    # -------------------------------------------------------------
    #   5.4 Strength
    # -------------------------------------------------------------

    # Clause 3.7 - Classification of cross-section, Table 2, Limiting width to thickness ratio
    @staticmethod
    def web_class(width, thickness, fy, *, loading):
        """Table 2(ii). Axial: supply printed b/tf; mid-depth bending: d/tw.
        For general nonuniform stress use web_general_limit for classes 1/2.
        """
        _positive(width, thickness, fy)
        limits = {"axial": (32, 36.8, 40.7), "mid-depth": (70, 80, 120)}
        return _classify(width / thickness, limits[loading], math.sqrt(250 / fy))

    @staticmethod
    def web_general_limit(fy, compression_fraction, *, section_class):
        """Table 2(ii). Limiting d/tw for Class 1 or 2, using r1 independently.
        For the symmetric mid-depth case use web_class. The two printed r2
        branches for Class 3 overlap and require an authoritative clarification.
        """
        _positive(fy, compression_fraction)
        r1 = compression_fraction
        if r1 > 1:
            raise ValueError("Compressed depth cannot exceed overall depth")
        upper, lower = {"Plastic": (384, 35), "Compact": (442, 40.2)}[section_class]
        coefficient = upper / (13*r1 - 1) if r1 > 0.5 else lower / r1
        return coefficient * math.sqrt(250 / fy)

    @staticmethod
    def Table2_web_OfI_H_box_section(depth, web_thickness, f_y, *, loading,
                                     compression_fraction=None, section_class=None):
        """Draft Table 2(ii). Return class for mid-depth/axial, or Pass/Fail
        for one requested general-stress Class 1 or 2. For axial use the printed
        axial-row dimension pair. A force in N cannot determine r1 and r2.
        """
        if loading != "general":
            return IS800_2025_Draft.web_class(depth, web_thickness, f_y, loading=loading)
        _positive(depth, web_thickness)
        limit = IS800_2025_Draft.web_general_limit(f_y, compression_fraction,
                                                  section_class=section_class)
        return "Pass" if depth/web_thickness <= limit else "Fail"

    @staticmethod
    def tube_class(diameter, thickness, fy, *, loading):
        """Table 2(vi). Outside diameter. Axial row has only a Class 3 limit."""
        _positive(diameter, thickness, fy)
        limits = {"moment": (47, 66, 85), "axial": (None, None, 86)}
        return _classify(diameter/thickness, limits[loading], 250/fy)

    @staticmethod
    def Table2_hollow_tube(diameter, thickness, f_y, load='Axial Compression', section_class='Plastic'):
        """Table 2(vi). An axial Plastic/Compact limit is not tabulated."""
        loading = {'Axial Compression': 'axial', 'Moment': 'moment'}[load]
        classes = ['Plastic', 'Compact', 'Semi-Compact', 'Slender']
        requested = section_class.capitalize()
        if requested == 'Semi-compact':
            requested = 'Semi-Compact'
        if requested not in classes[:3]:
            raise ValueError("Select Plastic, Compact or Semi-Compact")
        actual = IS800_2025_Draft.tube_class(diameter, thickness, f_y, loading=loading)
        if loading == 'axial' and requested in classes[:2]:
            return 'Not applicable'
        return 'Pass' if classes.index(actual) <= classes.index(requested) else 'Fail'

    @staticmethod
    def outstand_class(width, thickness, fy, *, stress="uniform", compression_fraction=None):
        """Table 2(i). Nonuniform rows only give Class 1 and 2 limits."""
        _positive(width, thickness, fy)
        scale = math.sqrt(250 / fy)
        if stress == "uniform":
            return _classify(width/thickness, (8.7, 9.7, 13.6), scale)
        if stress not in ("tip-compression", "tip-tension"):
            raise ValueError("Unknown stress distribution")
        if compression_fraction is None or not 0 < compression_fraction <= 1:
            raise ValueError("Supply r1 = compressed depth / overall depth")
        divisor = compression_fraction
        if stress == "tip-tension":
            divisor *= math.sqrt(compression_fraction)
        result = _classify(width/thickness, (8.7, 9.7, None), scale/divisor)
        if result == "Slender":
            raise NotImplementedError("Table 2(i) gives no nonuniform Class 3 limit")
        return result

    @staticmethod
    def Table2_i(width, thickness, f_y, section_type='Rolled'):
        """Table 2(i), uniform compression; same ratios for rolled and welded."""
        if section_type not in ('Rolled', 'Welded'):
            raise ValueError("Expected Rolled or Welded")
        return [IS800_2025_Draft.outstand_class(width, thickness, f_y), width/thickness]

    @staticmethod
    def Table2_iii(depth, thickness, f_y, classification_type='Neutral axis at mid-depth'):
        """Table 2(ii); general stress requires Table2_web_OfI_H_box_section."""
        loading = {'Neutral axis at mid-depth': 'mid-depth', 'Axial compression': 'axial'}[classification_type]
        return IS800_2025_Draft.web_class(depth, thickness, f_y, loading=loading)

    @staticmethod
    def Table2_iv(depth, thickness_web, f_y):
        """Table 2(ii), axial row. Supply applicable clear dimension and thickness."""
        return [IS800_2025_Draft.web_class(depth, thickness_web, f_y, loading='axial'),
                depth/thickness_web]

    @staticmethod
    def angle_class(b, d, thickness, fy, *, case):
        """Table 2(iii-v). For the contacting angle leg only d/t governs."""
        _positive(b, d, thickness, fy)
        scale = math.sqrt(250/fy)
        if case == "separated-axial":
            ok = max(b, d)/thickness <= 14.5*scale and (b+d)/thickness <= 22.3*scale
            return "Semi-Compact" if ok else "Slender"
        width = {"bending": max(b, d), "contact-leg": d}[case]
        return _classify(width/thickness, (8.7, 9.7, 14.5), scale)

    @staticmethod
    def Table2_vi(width, depth, thickness, f_y, force_type="Axial Compression"):
        """Table 2(iii-iv). Check both legs and, for axial load, the sum."""
        case = {'Axial Compression':'separated-axial', 'Bending':'bending',
                'Compression due to bending':'bending'}[force_type]
        grade = IS800_2025_Draft.angle_class(width,depth,thickness,f_y,case=case)
        return [grade, width/thickness, depth/thickness, (width+depth)/thickness]

    @staticmethod
    def Table2_vii(width, depth, thickness, f_y, force_type="Axial Compression"):
        """Table 2(v), outstanding leg in contact back-to-back."""
        if force_type not in ('Axial Compression','Bending','Compression due to bending'):
            raise ValueError('Unknown force type')
        grade = IS800_2025_Draft.angle_class(width,depth,thickness,f_y,case='contact-leg')
        return [grade, width/thickness, depth/thickness, (width+depth)/thickness]


    @staticmethod
    def Table2_x(outer_diameter, tube_thickness, f_y, load_type='axial compression'):
        """Table 2(vi). Return the circular tube element class."""
        loading = {'axial compression':'axial','moment':'moment'}[load_type.lower()]
        return IS800_2025_Draft.tube_class(outer_diameter,tube_thickness,f_y,loading=loading)
    

    # ==========================================================================
    """    SECTION  3     GENERAL DESIGN REQUIREMENTS   """

    @staticmethod
    def maximum_slenderness(row, *, sag_avoided=False):
        """Table 3. Rows i-vi numbered 1-6. None denotes footnote exemption
        for an applicable tension member. Caller establishes row applicability.
        """
        limit = {1: 180, 2: 180, 3: 250, 4: 300, 5: 350, 6: 400}[row]
        if sag_avoided and row in (5, 6):
            return None
        return limit

    @staticmethod
    def cl_3_8_max_slenderness_ratio(Type=1):
        """Table 3, clause 10.9.1. Numbering 1-6 follows the six printed cases."""
        return IS800_2025_Draft.maximum_slenderness(Type)
    # ==========================================================================
    """    SECTION  4     METHODS OF STRUCTURAL ANALYSIS   """
    # ==========================================================================
    """    SECTION  5     LIMIT STATE DESIGN   """
    # -------------------------------------------------------------
    #   5.4 Strength
    # -------------------------------------------------------------

    # Table 5 Partial Safety Factors for Materials, gamma_m (dict)
    cl_5_4_1_Table_5 = {"gamma_m0": {'yielding': 1.10, 'buckling': 1.10},
                        "gamma_m1": {'ultimate_stress': 1.25},
                        "gamma_mf": {KEY_DP_FAB_SHOP: 1.25, KEY_DP_FAB_FIELD: 1.25},
                        "gamma_mb": {KEY_DP_FAB_SHOP: 1.25, KEY_DP_FAB_FIELD: 1.25},
                        "gamma_mr": {KEY_DP_FAB_SHOP: 1.25, KEY_DP_FAB_FIELD: 1.25},
                        "gamma_mw": {KEY_DP_FAB_SHOP: 1.25, KEY_DP_FAB_FIELD: 1.50}
                        }
    
    # ------------------------------------------------------------
    #   5.6.1 Deflection
    # -------------------------------------------------------------

#     cl_5_6_1_vertical_deflection_Table_6 = {
        
# Type of structure      Load Type                           Member              Supporting                          Deflection Limit
# Industrial building    Live Load                            Purlins and Girts    Elastic cladding                     Span/150
# Industrial building    Live Load                            Purlins and Girts    Brittle cladding                     Span/180
# Industrial building    Live Load                            Simple span          Elastic cladding                     Span/240
# Industrial building    Live Load                            Simple span          Brittle cladding                     Span/300
# Industrial building    Live Load                            Cantilever span      Elastic cladding                     Span/120
# Industrial building    Live Load                            Cantilever span      Brittle cladding                     Span/150
# Industrial building    Live Load                            Rafter supporting    Profiled Metal Sheeting              Span/180
# Industrial building    Live Load                            Rafter supporting    Plastered Sheeting                   Span/240
# Industrial building    Crane Load(Manual operation)         Gantry               Crane                                Span/500
# Industrial building    Crane load(Electric operation up to 50t)  Gantry          Crane                                Span/750
# Industrial building    Crane load(Electric operation over 50t)  Gantry           Crane                                Span/1000
# Other buildings        Live Load                            Floor and Roof       Elements not susceptible to cracking Span/300
# Other buildings        Live Load                            Floor and Roof       Element susceptible to cracking      Span/360
# Other buildings        Live Load                            Cantilever Span      Elements not susceptible to cracking Span/150
# Other buildings        Live Load                            Cantilever Span      Element susceptible to cracking      Span/180
# Highway Bridges        Live Load                            Simple span          NA                                    Span/600
# Railway Bridges        Live Load                            Simple span          NA                                    Span/600
# Highway Bridges        Dead Load                            Simple span          NA                                    Span/800
# Railway Bridges        Dead Load                            Simple span          NA                                    Span/800
# Highway Bridges        Live Load                            Cantilever span      NA                                    Span/400
# Railway Bridges        Live Load                            Cantilever span      NA                                    Span/400
# Highway Bridges        Dead Load                            Cantilever span      NA                                    Span/800
# Railway Bridges        Dead Load                            Cantilever span      NA                                    Span/800


    # }

    # ==========================================================================
    """    SECTION  6     DESIGN OF TENSION MEMBERS   """

    # ------------------------------------------------------------
    #   6.2 Design Strength Due to Yielding of Gross Section
    # -------------------------------------------------------------

    @staticmethod
    def tension_yield(ag, fy):
        """13.2, gross section yielding strength (N)."""
        _positive(ag, fy)
        return ag*fy/1.1

    @staticmethod
    def cl_6_2_tension_yielding_strength(A_g, f_y):
        """Draft 13.2. Retained project calculation and units."""
        gamma_m0 = IS800_2025_Draft.material_factors["gamma_m0"]['yielding']
        T_dg = A_g * f_y / gamma_m0
        return T_dg
    # ------------------------------------------------------------
    #   6.3 Design Strength Due to Rupture of Critical Section
    # -------------------------------------------------------------

    # cl.6.3.1 Plates
    @staticmethod
    def plate_rupture(an, fu):
        """13.3.1, net section rupture (N). Supply effective net area."""
        _positive(an, fu)
        return .9*an*fu/1.25

    @staticmethod
    def cl_6_3_1_tension_rupture_strength(A_n,f_u):
        """Draft 13.3.1. Retained project calculation and units."""
        gamma_m1 = IS800_2025_Draft.material_factors["gamma_m1"]['ultimate_stress']
        T_dn = 0.9*A_n*f_u/gamma_m1
        return T_dn
    #   6.4 Design Strength Due to Block Shear
    # -------------------------------------------------------------

    # cl. 6.4.1 Block shear strength of bolted connections
    @staticmethod
    def block_shear(avg, avn, atg, atn, fu, fy):
        """13.4.1, bolted end connection. Evaluate each candidate failure path."""
        _positive(avg, avn, atg, atn, fu, fy)
        return min(avg*fy/(math.sqrt(3)*1.1) + .9*atn*fu/1.25,
                   .9*avn*fu/(math.sqrt(3)*1.25) + atg*fy/1.1)

    @staticmethod
    def cl_6_4_1_block_shear_strength(A_vg, A_vn, A_tg, A_tn, f_u, f_y):
        """Draft 13.4.1. Retained project calculation and units."""
        gamma_m0 = IS800_2025_Draft.material_factors["gamma_m0"]['yielding']
        gamma_m1 = IS800_2025_Draft.material_factors["gamma_m1"]['ultimate_stress']
        T_db1 = A_vg * f_y / (math.sqrt(3) * gamma_m0) + 0.9 * A_tn * f_u / gamma_m1
        T_db2 = 0.9 * A_vn * f_u / (math.sqrt(3) * gamma_m1) + A_tg * f_y / gamma_m0
        return min(T_db1, T_db2)

    # ==========================================================================
    """    SECTION  7     DESIGN OF COMPRESS1ON MEMBERS   """

    # -------------------------------------------------------------
    #   7.4 Column Bases
    # -------------------------------------------------------------

    # cl. 7.4.1, General
    @staticmethod
    def bearing_pressure(fck_concrete, fck_bedding, pedestal_area, base_contact_area):
        """14.4.1. Concrete and bedding characteristic cube strengths in MPa."""
        _positive(fck_concrete, fck_bedding, pedestal_area, base_contact_area)
        fck = min(fck_concrete, fck_bedding)
        return min(0.45 * math.sqrt(pedestal_area/base_contact_area), 0.9) * fck

    # cl. 7.1, Design strength
    @staticmethod
    def member_compression_ok(area, fcd, axial):
        """14.1.2. Compression force magnitude in N."""
        _positive(area, fcd)
        if not math.isfinite(axial) or axial < 0:
            raise ValueError("Supply a compression force magnitude")
        return axial < area*fcd

    @staticmethod
    def cl_7_1_2_design_compressisive_strength_member( effective_area , design_compressive_stress , axial_load ):
        """Draft 14.1.2. Retained project calculation and units."""
        design_compressive_strength= effective_area * design_compressive_stress                     #area in mm2,stress in kN/mm2
        if axial_load < design_compressive_strength:                                                #kN
            check = 'pass'
        else:
            check = 'fail'
        return check                                                                                #str

    # cl. 7.2.2 Effective Length of Prismatic Compression Members
    @staticmethod
    def effective_length(length, first_end, second_end):
        """14.2.2 Table 11. 'guided' permits translation and restrains rotation."""
        _positive(length)
        ends = tuple(sorted((first_end, second_end)))
        factors = {("fixed","free"): 2, ("guided","pinned"): 2,
                   ("pinned","pinned"): 1, ("fixed","guided"): 1.2,
                   ("fixed","pinned"): .8, ("fixed","fixed"): .65}
        return factors[ends]*length

    @staticmethod
    def truss_length(length, *, plane, restraint_factor=None):
        """14.2.4. General truss compression members; see 14.5 for angle struts."""
        _positive(length)
        if plane == "out-of-plane":
            return length
        if plane != "in-plane" or restraint_factor is None or not .7 <= restraint_factor <= 1:
            raise ValueError("In-plane restraint requires a justified factor in [0.7, 1]")
        return length*restraint_factor

    # cl. 7.1.2.1, Design stress
    @staticmethod
    def column_table(curve, kl_over_r, fy):
        """Tables 8 and 9. Returns (chi, fcd in MPa) for exact printed grid points."""
        rows = _COLUMN_TABLES[curve]
        try:
            index = _COLUMN_FY.index(fy)
            chi, stress = rows[kl_over_r]
        except (ValueError, KeyError) as exc:
            raise ValueError("Use an explicit tabulated fy and KL/r") from exc
        return chi[index], stress[index]

    @staticmethod
    def compression_stress(chi, fy):
        """14.1.2. Design compressive stress from governing reduction factor."""
        _positive(chi, fy)
        return min(chi,1)*fy/1.1

    # Cl. 7.1.1, Cl.7.1.2.1, Imperfection Factor
    @staticmethod
    def imperfection_factor(curve):
        """Table 7. Column imperfection factor."""
        return {"a0": 0.13, "a": 0.21, "b": 0.34, "c": 0.49, "d": 0.76}[curve]

    # cl. 7.1.2.1, Buckling Class of Cross-Sections
    @staticmethod
    def buckling_curves(section, fy, *, h=None, b=None, tf=None, tw=None, thick_weld=None):
        """Table 10. Return curve keys in z-z, y-y order."""
        _positive(fy)
        high = fy > 420
        if section == "rolled-I":
            _positive(h, b, tf)
            if h/b == 1.2 or (h/b > 1.2 and tf > 100):
                raise NotImplementedError("This geometry has no explicit Table 10 row")
            if h/b > 1.2 and tf <= 40:
                return ("a0", "a") if high else ("a", "b")
            if tf <= 100:
                return ("a", "b") if high else ("b", "c")
            return ("c", "c") if high else ("d", "d")
        if section == "welded-I":
            _positive(tf)
            if tf == 40:
                raise NotImplementedError("Table 10 prints strict inequalities at 40 mm")
            return ("b", "c") if tf < 40 else ("c", "d")
        if section in ("welded-box", "cruciform"):
            if thick_weld is None:
                raise ValueError("Identify whether thick welds are present")
            curve = "b"
            if thick_weld:
                _positive(b, tf, h, tw)
                if b/tf < 30 and h/tw < 30:
                    curve = "c"
        else:
            curve = {"hot-hollow": "a0" if high else "a",
                     "cold-hollow": "c" if high else "b",
                     "channel": "c", "angle": "c", "tee": "c", "solid": "c",
                     "built-up": "c"}[section]
        return curve, curve

    # Draft Table 9: Request class c explicitly only when applicable. No automatic class assignment.

    # Draft Table 9(d): Old DataFrame replaced by exact coordinate lookup for all curves.
        
    

    @staticmethod
    def one_leg_angle_stress(length_aa, radius_aa, b1, b2, t, fy, chi_aa, *,
                             connection, fixed_fraction, E=200000):
        """14.5.1.2 & Table 12. chi_aa from Table 8(c) for lambda_aa.
        fixed_fraction 0 = hinged, 1 = fixed. Return fcde in MPa.
        Separate chi input avoids silently choosing between inconsistent 14.1.2.1
        printed equation and Table 8. Use the actual connected-leg a-a axis.
        """
        _positive(length_aa, radius_aa, b1, b2, t, fy, E, chi_aa)
        if chi_aa > 1 or not 0 <= fixed_fraction <= 1:
            raise ValueError("Invalid reduction factor or restraint fraction")
        hinged, fixed = {
            "welded-or-multiple-bolts": ((.401,.420,-1.040),(.798,.563,-2.072)),
            "single-bolt": ((.374,.415,-2.072),(.418,.547,-1.400)),
        }[connection]
        scale = math.sqrt(fy/E)/math.pi
        slender_aa = length_aa/radius_aa * scale
        slender_leg = (b1+b2)/(2*t) * scale
        def factor(row):
            a, b, c = row
            return a + b*slender_aa + c*slender_leg
        kf = factor(hinged) + fixed_fraction*(factor(fixed)-factor(hinged))
        if kf <= 0:
            raise ValueError("Non-positive Kf; review applicability")
        return kf * chi_aa * fy / 1.1
    # ==========================================================================
    """    SECTION  8     DESIGN OF MEMBERS SUBJECTED TO BENDING   """

    # -------------------------------------------------------------
    #   8.4 Shear
    # -------------------------------------------------------------
    @staticmethod
    def web_shear_buckling_required(d, tw, fyw, *, kv=None):
        """15.4.2.1. Omit kv only for a web without stiffeners."""
        _positive(d, tw, fyw)
        factor = 1
        if kv is not None:
            _positive(kv)
            factor = math.sqrt(kv/5.35)
        return d/tw > 67*math.sqrt(250/fyw)*factor

    @staticmethod
    def cl_8_2_1_web_buckling(d, tw, e):
        d_tw = d / tw
        if d_tw <= 67*e:
            return False
        return True

    @staticmethod
    def low_shear_moment(section_class, zp, ze, fy, support):
        """15.2.1.2. Laterally supported beam, low shear and eligible web. N mm."""
        _positive(zp, ze, fy)
        modulus = {"Plastic": zp, "Compact": zp, "Semi-Compact": ze}[section_class]
        cap = {"simply-supported": 1.2, "cantilever": 1.5}[support]
        return min(modulus, cap*ze)*fy/1.10


    @staticmethod
    def beam_high_shear(v, vd):
        """15.2.1.2-3. Supply magnitudes in the same units."""
        _positive(vd)
        if not math.isfinite(v) or v < 0:
            raise ValueError("Supply nonnegative shear magnitude")
        return v > .6*vd

    @staticmethod
    def holes_may_be_ignored(net_to_gross, fy, fu):
        """15.2.1.4(a). True when tension flange holes meet the area criterion."""
        _positive(net_to_gross, fy, fu)
        if net_to_gross > 1:
            raise ValueError("Net area exceeds gross area")
        return net_to_gross >= (fy/fu)*(1.25/1.1)/.9

    @staticmethod
    def edge_shear_lag_width(width, length_between_inflections, *, element):
        """15.2.1.5. Conservative effective width in mm."""
        _positive(width, length_between_inflections)
        divisor = {"outstand":20, "internal":10}[element]
        return min(width,length_between_inflections/divisor)

    @staticmethod
    def ltb_moment(section_class, zp, ze, fbd, *, zeff=None):
        """15.2.2. N mm. Class 4 requires effective modulus at compression fibre."""
        modulus = {"Plastic": zp, "Compact": zp, "Semi-Compact": ze, "Slender": zeff}[section_class]
        if modulus is None:
            raise ValueError("Supply effective modulus for class 4")
        _positive(modulus, fbd)
        return modulus*fbd

    @staticmethod
    def cl_8_2_2_Unsupported_beam_bending_compressive_stress(X_lt, fy, gamma_mo):
        return X_lt * fy / gamma_mo

    @staticmethod
    def cl_8_2_2_Unsupported_beam_bending_stress_reduction_factor(phi_lt, lambda_lt):
        si = 1 / ( phi_lt + (phi_lt **2 - lambda_lt **2) ** 0.5)
        if si > 1.0:
            si = 1.0
        return si

    @staticmethod
    def cl_8_2_2_Unsupported_beam_bending_phi_lt(alpha_lt, lambda_lt):
        a = 0.5 * ( 1 + alpha_lt * ( lambda_lt - 0.2) + lambda_lt ** 2)
        # print(alpha_lt, lambda_lt, a)
        return a

    @staticmethod
    def cl_8_2_2_Unsupported_beam_bending_non_slenderness( E, meu,Iy, It, Iw, Llt,beta_b, Zp, hf,ry, tf):
        ''' Author : Rutvik Joshi
        Clauses: 8.2.2.1 and Annex E
        '''
        G = E/(2+2*meu)
        fcrb = (1.1 * math.pi**2 * E/(Llt/ry)**2) * math.sqrt(1 + (((Llt/ry)/(hf/tf))**2) / 20)
        _ = math.sqrt((math.pi**2 * E * Iy/Llt**2)*(G *It + (math.pi**2 * E * Iw/Llt**2) ))
        __ = beta_b * Zp * fcrb
        ___ = (math.pi**2 * E * Iy * hf/Llt**2)/2 * math.sqrt(1 + (((Llt/ry)/(hf/tf))**2) / 20 )
        return [min(_,__,___), fcrb]

    @staticmethod
    def cl_8_2_2_Unsupported_beam_bending_fcrb(E, Llt_ry, hf_tf):
        ''' Author : Rutvik Joshi
        Clauses: 8.2.2.1 and Annex E
        '''
        fcrb = 1.1 * math.pi**2 * E * (1 + (Llt_ry/hf_tf)**2/20)**0.5 / Llt_ry
        return fcrb
    @staticmethod
    def cl_8_2_2_1_elastic_buckling_moment(betab, Zp, Ze, fy, Mcr, fcrb = 0):
        if (betab * Zp * fy / Mcr) ** 0.5 <= (1.2 * Ze * fy / Mcr) ** 0.5:
            return (betab * Zp * fy / Mcr) ** 0.5
        else:
            return (1.2 * Ze * fy / Mcr) ** 0.5

    @staticmethod
    def cl_8_2_2_1_elastic_buckling_moment_fcrb( fy, fcrb=0):

        return math.sqrt(fy/fcrb)
    @staticmethod
    def cl_8_3_1_EffLen_Simply_Supported(Torsional, Warping, length, depth, load) :
        """ Calculate the Effective Length for Simply Supported Beams as per Table 15 Cl 8.3.1

        Args:
            Torsional Restraint: Type of Restraint (string)
            Warping Restraint: Type of Restraint (string)
            depth(d): depth of the element in mm (float or int)
            length(l): length of span in mm (float or int)
            f_y: yield stress of the section material in MPa (float or int)
            load: Type of load in member ('Normal') ('Destabilizing')


        Returns:
            Effective length (float)

        Reference: Table 15 Cl 8.3.1, IS 800:2007

        """
        if load == KEY_DISP_LOAD1:
            if Torsional == Torsion_Restraint1:
                if Warping == Warping_Restraint1 :
                    length = 0.80 * length
                elif Warping == Warping_Restraint2 :
                    length = 0.75 * length
                # elif Warping ==Warping_Restraint1 :
                #     length = 0.80 * length
                elif Warping == Warping_Restraint4 :
                    length = 0.85 * length
                elif Warping == Warping_Restraint5 :
                    length = 1.00 * length
            elif Torsional == Torsion_Restraint2 and Warping == Warping_Restraint5 :
                length = length + 2 * depth
            elif Torsional == Torsion_Restraint3 and Warping == Warping_Restraint5 :
                length = 1.2 * length + 2 * depth
        elif load == KEY_DISP_LOAD2:
            if Torsional == Torsion_Restraint1:
                if Warping == Warping_Restraint1 :
                    length = 0.85 * length
                if Warping == Warping_Restraint2 :
                    length = 0.9 * length
                if Warping == Warping_Restraint1 :
                    length = 0.95 * length
                if Warping == Warping_Restraint4 :
                    length = 1.00 * length
                if Warping == Warping_Restraint5 :
                    length = 1.20 * length
            elif Torsional == Torsion_Restraint2 and Warping == Warping_Restraint5 :
                length = 1.2 * length + 2 * depth
            elif Torsional == Torsion_Restraint3 and Warping == Warping_Restraint5 :
                length = 1.4 * length + 2 * depth
        return length

    @staticmethod
    def cl_8_3_3_EffLen_Cantilever(Support, Top, length, load) -> float:
        """ Calculate the Effective Length for Simply Supported Beams as per Table 16 Cl 8.3.3

        Args:
            Support Restraint: Type of Restraint (string)
            Warping Restraint: Type of Restraint (string)
            depth(d): depth of the element in mm (float or int)
            length(l): length of span in mm (float or int)
            f_y: yield stress of the section material in MPa (float or int)
            load: Type of load in member ('Normal') ('Destabilizing')


        Returns:
            Effective length (float)

        Reference: Table 15 Cl 8.3.1, IS 800:2007

        """
        if load == KEY_DISP_LOAD1:
            if Support == Support1:
                if Top == Top1:
                    length = 3.00 * length
                if Top == Top2:
                    length = 2.7 * length
                if Top == Top3:
                    length = 2.40 * length
                if Top == Top4:
                    length = 2.1 * length

            elif Support == Support2:
                if Top == Top1:
                    length = 2.00 * length
                if Top == Top2:
                    length = 1.8 * length
                if Top == Top3:
                    length = 1.60 * length
                if Top == Top4:
                    length = 1.4 * length


            elif Support == Support3:

                if Top == Top1:
                    length = 1.00 * length

                if Top == Top2:
                    length = 0.9 * length

                if Top == Top3:
                    length = 0.80 * length

                if Top == Top4:
                    length = 0.7 * length

            elif Support == Support4:
                if Top == Top1:
                    length = 0.80 * length
                if Top == Top2:
                    length = 0.7 * length
                if Top == Top3:
                    length = 0.6 * length
                if Top == Top4:
                    length = 0.5 * length
        elif load == KEY_DISP_LOAD2:
            if Support == Support1:
                if Top == Top1:
                    length = 7.50 * length
                if Top == Top2:
                    length = 7.5 * length
                if Top == Top3:
                    length = 4.50 * length
                if Top == Top4:
                    length = 3.6 * length

            elif Support == Support2:
                if Top == Top1:
                    length = 5.00 * length
                if Top == Top2:
                    length = 5 * length
                if Top == Top3:
                    length = 3.0 * length
                if Top == Top4:
                    length = 2.4 * length


            elif Support == Support3:

                if Top == Top1:
                    length = 2.50 * length

                if Top == Top2:
                    length = 2.5 * length

                if Top == Top3:
                    length = 1.50 * length

                if Top == Top4:
                    length = 1.2 * length

            elif Support == Support4:
                if Top == Top1:
                    length = 1.40 * length
                if Top == Top2:
                    length = 1.4 * length
                if Top == Top3:
                    length = 0.6 * length
                if Top == Top4:
                    length = 0.5 * length
        return length
    # cl. 8.4.1 shear strength of bolted connections
    @staticmethod
    def cl_8_4_design_shear_strength(A_vg, f_y):
        """ Calculate the design shear strength in yielding as per cl. 8.4

        Args:
             A_vg: Gross area of the component in square mm (float)
             f_y: Yield stress of the component material in MPa (float)

        Returns:
             Design shear strength in yielding of the component in N

        """
        gamma_m0 = IS800_2007.cl_5_4_1_Table_5["gamma_m0"]['yielding']
        V_d = ((A_vg * f_y) / (math.sqrt(3) * gamma_m0))  # N

        return V_d

    # cl 8.2.1.2 design bending strength of the cross-section
    @staticmethod
    def cl_8_2_1_2_design_moment_strength(Z_e, Z_p, f_y, section_class=''):
        """ Calculate the design bending strength as per cl. 8.2.1.2
        Args:
            Z_e: Elastic section modulus of the cross-section in cubic mm (float)
            Z_p: Plastic section modulus of the cross-section in cubic mm (float)
            f_y: Yield stress of the component material in MPa (float)
            section_class: Classification of the section (plastic, compact or semi-compact) as per Table 2 (str)
        Returns:
            Design bending strength of the cross-section in N-mm (float)
        """
        gamma_m0 = IS800_2007.cl_5_4_1_Table_5["gamma_m0"]['yielding']

        if section_class == 'semi-compact':
            M_d = (Z_e * f_y) / gamma_m0  # N-mm
        else:  # 'compact'
            M_d = (1.0 * Z_p * f_y) / gamma_m0  # N-mm

        return M_d

    @staticmethod
    def cl_8_4_2_1_web_buckling_stiff(d, tw, e,type = 1, kv = None):
        '''nominal shear strength, Vn,of webs with or without
        intermediate stiffeners as governed by buckling

        Author: Rutvik Joshi    '''
        d_tw = d / tw
        if type == 1 and d_tw <= 67 * e:
            return False
        elif type == 2 and d_tw <= 67 * e * math.sqrt(kv/5.35):
            return False
        return True

    # @staticmethod
    # def cl_8_4_2_2_ShearBuckling_Simple_postcritical(d, tw,c,mu,fyw,A_v,support):
    #     '''based on the shear
    #         buckling strength can be used for webs of Isection
    #         girders, with or without intermediate
    #         transverse stiffener, provided that the web has
    #         transverse stiffeners at the supports.
    #
    #     Author: Rutvik Joshi    '''

    @staticmethod
    def cl_8_4_2_2_K_v_Simple_postcritical(support, c = 0, d = 1):

        if support == 'only support':
            K_v = 5.35
        else:
            if c/d < 1:
                K_v = 4 + 5.35/(c/d)**2
            else:
                K_v = 5.35 + 4/(c/d)**2
        return K_v

    @staticmethod
    def cl_8_4_2_2_tau_crc_Simple_postcritical(K_v, E,mu, d, tw):
        # print('K_v',K_v,'\n E',E,'\nmu',mu,' d',d,' tw',tw)
        tau_crc = (K_v * math.pi**2 * E)/(12*(1-mu**2)*(d/tw)**2)

        return tau_crc

    @staticmethod
    def cl_8_4_2_2_lambda_w_Simple_postcritical(fyw, tau_crc):
        # print('fyw',fyw,'\n tau_crc',tau_crc)

        lambda_w = math.sqrt(fyw/(math.sqrt(3) * tau_crc))

        return lambda_w

    @staticmethod
    def cl_8_4_2_2_tau_b_Simple_postcritical(lambda_w, fyw):
        # print('fyw',fyw,' lambda_w',lambda_w)
        if lambda_w <= 0.8:
            tau_b = fyw / math.sqrt(3)
        elif lambda_w < 1.2 and lambda_w > 0.8:
            tau_b = (1 - 0.8*(lambda_w - 0.8)) * fyw / math.sqrt(3)
        elif lambda_w >= 1.2:
            tau_b = fyw / (math.sqrt(3) * lambda_w ** 2)

        return tau_b

    @staticmethod
    def cl_8_4_2_2_Vcr_Simple_postcritical(tau_b, A_v):
        # print('tau_b',tau_b,'\n A_v',A_v)

        V_cr = A_v * tau_b

        return V_cr

    @staticmethod
    def cl_8_4_2_2_Mfr_TensionField(bf, tf, fyf, Nf, gamma_mo):
        '''based on the post-shear buckling
            strength, may be used for webs with
            intermediate transverse stiffeners, in addition
            to the transverse stiffeners at supports, provided
            the panels adjacent to the panel under tension
            field action, or the end posts provide anchorage
            for the tension fields

        Author: Rutvik Joshi    '''

        M_fr = 0.25 * bf * tf ** 2 * fyf * (1 - (Nf / (bf * tf * fyf / gamma_mo)) ** 2)
        print(M_fr, 'M_fr')
        return  M_fr
    @staticmethod
    def cl_8_4_2_2_TensionField( c, d, tw, fyw, bf,tf, fyf,Nf, gamma_mo, A_v,tau_b,V_p):
        '''based on the post-shear buckling
            strength, may be used for webs with
            intermediate transverse stiffeners, in addition
            to the transverse stiffeners at supports, provided
            the panels adjacent to the panel under tension
            field action, or the end posts provide anchorage
            for the tension fields

        Author: Rutvik Joshi    '''

        if c == 0:
            phi = 90  
        else:
            phi = math.atan(d/c) * 180/math.pi
        M_fr = 0.25 * bf * tf**2 * fyf*(1-(Nf/(bf * tf * fyf / gamma_mo))**2)
        print('phi',phi,'\n Nf',Nf,M_fr,'M_fr',phi*math.pi/180)
        s = 2 * math.sqrt(M_fr / (fyw * tw)) / math.sin(phi*math.pi/180)
        if s <= c:
            pass
        else:
            s == c
        w_tf = d * math.cos(phi*math.pi/180) + (c-2*s)*math.sin(phi*math.pi/180)
        sai = 1.5 * tau_b * math.sin(2*phi*math.pi/180)
        fv = math.sqrt(fyw**2 - 3 * tau_b**2 + sai**2) - sai
        V_tf = A_v * tau_b + 0.9 * w_tf * tw * fv * math.sin(phi*math.pi/180)/ 10 ** 3
        if V_tf <= V_p:
            pass
        else:
            V_tf == V_p
            print('phi',phi,'\n M_fr',M_fr,'\n s',s, '\n c',c, '\n w_tf', w_tf, '\n sai',sai,'\n fv',fv,'\n V_tf',V_tf,'\n V_p',V_p)
        return phi,M_fr,s, w_tf,sai,fv,V_tf

    @staticmethod
    def cl_8_4_2_2_TensionField_unequal_Isection(
    c, d, tw, fyw,
    bf_top, tf_top, bf_bot, tf_bot,
    Nf, gamma_m0, A_v, tau_b):
        """
        Tension‐field method per IS 800:2007 Cl. 8.4.2.2 for unequal flanges.

        Parameters:
        c       : float : panel width (mm)
        d       : float : web depth (mm)
        tw      : float : web thickness (mm)
        fyw     : float : web yield stress (N/mm²)
        bf_top  : float : top flange width (mm)
        tf_top  : float : top flange thickness (mm)
        bf_bot  : float : bottom flange width (mm)
        tf_bot  : float : bottom flange thickness (mm)
        Nf      : float : axial force in each flange (kN → N·mm units consistent)
        gamma_m0: float : partial safety factor
        A_v     : float : gross web area = d*tw (mm²)
        tau_b   : float : post‐buckling shear stress of web (N/mm²)
        V_p     : float : plastic shear strength V_np (kN)

        Returns:
        tuple: (phi, Mfr_top, Mfr_bot, s_top, s_bot, w_tf, psi, fv, V_tf)
        """

        # 1) Tension‐field angle φ
        if c == 0:
            phi = 90.0
        else:
            phi = math.degrees(math.atan((d / c) / 1.5))

        # 2) Reduced plastic moment of each flange
        def Mfr(bf, tf):
            Mp = 0.25 * bf * tf**2 * fyw
            ratio = Nf / (bf * tf * fyw / gamma_m0)
            if ratio >= 1:
                return 0
            else:
                return Mp * (1 - ratio**2)

        Mfr_t = Mfr(bf_top, tf_top)
        Mfr_b = Mfr(bf_bot, tf_bot)

        # 3) s‐values for each flange, limited to c

        sinφ = math.sin(math.radians(phi))
        if sinφ == 0:
            s_t= 0
            s_b= 0
        else:
            s_t = min(2 * math.sqrt(Mfr_t / (fyw * tw)) / sinφ, c)
            s_b = min(2 * math.sqrt(Mfr_b / (fyw * tw)) / sinφ, c)


        # 4) Width of the tension field w_tf
        w_tf = d * math.cos(math.radians(phi)) - (c - s_t - s_b) * sinφ

        # 5) Field yield strength f_v
        psi = 1.5 * tau_b * math.sin(2 * math.radians(phi))
        fv  = math.sqrt(fyw**2 - 3 * tau_b**2 + psi**2) - psi

        # 6) Nominal shear resistance V_tf (kN)
        V_tf = (A_v * tau_b + 0.9 * w_tf * tw * fv * sinφ)
        V_p = d * tw * fyw / (math.sqrt(3) * gamma_m0)  # Plastic shear strength
        V_tf = min(V_tf, V_p)

        return phi, Mfr_t, Mfr_b, s_t, s_b, w_tf, psi, fv, V_tf

    @staticmethod
    def cl_8_5_1_EndPanel(c, d, tw, fyw, bf, tf, fyf, Nf, gamma_mo, A_v, tau_b, V_p):
        '''The design of end panels in girders in which the interior
        panel (panel A) is designed using tension field action
        shall be carried in accordance with the provisions given
        herein.
        only simple post critical method design
        Author: Rutvik Joshi    '''

        phi = math.atan(d / c) * 180 / math.pi
        M_fr = 0.25 * bf * tf ** 3 * fyf * (1 - (Nf / (bf * tf * fyf / gamma_mo)) ** 2)
        print('phi', phi, '\n Nf', Nf, M_fr, 'M_fr', phi * math.pi / 180)
        s = 2 * math.sqrt(M_fr / (fyw * tw)) / math.sin(phi * math.pi / 180)
        if s <= c:
            pass
        else:
            s == c
        w_tf = d * math.cos(phi * math.pi / 180) + (c - 2 * s) * math.sin(phi * math.pi / 180)
        sai = 1.5 * tau_b * math.sin(2 * phi * math.pi / 180)
        fv = math.sqrt(fyw ** 2 - 3 * tau_b ** 2 + sai ** 2) - sai
        V_tf = A_v * tau_b + 0.9 * w_tf * tw * fv * math.sin(phi * math.pi / 180) / 10 ** 3
        if V_tf <= V_p:
            pass
        else:
            V_tf == V_p
        return phi, M_fr, s, w_tf, sai, fv, V_tf
    

    @staticmethod
    def cl_8_6_1_1_plate_girder_minimum_web_a(D,tw,epsilon,tf_top,tf_bot):
        d = D - (tf_top + tf_bot)
        if d/tw < 200 * epsilon:
            return True
        else:   
            return False

    @staticmethod   
    def cl_8_6_1_1_and_8_6_1_2_web_thickness_check(d, tw, eps, stiffener_type, c=None):
        """
        Check minimum web thickness requirements as per IS 800:2007 Cl. 8.6.1.1 & 8.6.1.2

        Parameters:
        d (float): Depth of web (mm)
        tw (float): Thickness of web (mm)
        eps (float): ε = sqrt(250/fy) where fy is yield strength of steel (N/mm^2)
        stiffener_type (str): Type of stiffening provided. Options:
            - "no_stiffener"
            - "transverse_only"
            - "transverse_and_two_longitudinal_neutral"
            - "transverse_and_one_longitudinal_compression"
        c (float): Spacing of transverse stiffeners (mm), required for some types

        Returns:
        dict: Dictionary with result of the web thickness check.
        """

        results = {}
        # print(stiffener_type)
        if stiffener_type == "no_stiffener" or c > 3 * d:
            ratio = d / tw
            # print("Web Ratio:", ratio)
            limit_serv = 200 * eps
            limit_buckling = 345 * (eps ** 2)
            limit = min(limit_serv, limit_buckling)
            results["Limit"] = limit
            if ratio <= limit:
                return True
            else:
                return False

        elif stiffener_type == "transverse_only":
            if c is None:

                return False #{"Error": "Spacing 'c' is required for 'transverse_only' stiffeners."}
            # print("c:", c, "d:", d, "tw:", tw, "eps:", eps)
            if 3 * d >= c and c >= 1.5 * d:
                ratio_serv = d / tw
                ratio_buckling = d / tw
                limit_serv = 200 * eps
                limit_buckling = 345 * (eps ** 2)
            elif 1.5 * d > c and c >= d:
                ratio_serv = d / tw
                ratio_buckling = d / tw
                limit_serv = 200 * eps
                limit_buckling = 345 * eps
            elif 0.74 * d <= c and c < d:
                ratio_serv = c / tw
                ratio_buckling = d / tw
                limit_serv = 200 * eps
                limit_buckling = 345 * eps
            elif c < 0.74 * d:
                ratio_serv = d / tw
                ratio_buckling = d / tw
                limit_serv = 270 * eps
                limit_buckling = 345 * eps
            else:
                # print('Transverse only')
                return False #{"Error": "Invalid range for spacing 'c'."}


            if ratio_serv <= limit_serv and ratio_buckling <= limit_buckling:
                return True
            else:
                return False

        elif stiffener_type == "transverse_and_two_longitudinal_neutral":
            if c >= 1.5 * d :
                ratio = d / tw
                limit_serv = 400 * eps
                limit_buckling = 345 * (eps ** 2)
                limit = min(limit_serv, limit_buckling)

            else:
                ratio = d / tw
                limit_serv = 400 * eps
                limit_buckling = 345 * eps
                limit = min(limit_serv, limit_buckling)

            if ratio <= limit:
                return True
            else:
                return False

        elif stiffener_type == "transverse_and_one_longitudinal_compression":
            if c is None:
                return False #{"Error": "Spacing 'c' is required for compression flange restraint."}

            if 2.4 * d >= c and c >= 1.5 * d:
                ratio_serv = d / tw
                ratio_buckling = d / tw
                limit_serv = 250 * eps
                limit_buckling = 345 * (eps ** 2)
            elif 1.5 * d > c and c >= d:
                ratio_serv = d / tw
                ratio_buckling = d / tw
                limit_serv = 250 * eps
                limit_buckling = 345 * eps
            elif 0.74 * d <= c and c < d:
                ratio_serv = c / tw
                ratio_buckling = d / tw
                limit_serv = 250 * eps
                limit_buckling = 345 * eps
            elif c < 0.74 * d:
                ratio_serv = d / tw
                ratio_buckling = d / tw
                limit_serv = 340 * eps
                limit_buckling = 345 * eps
            else:
                return False #{"Error": "Invalid range for spacing 'c'."}

            if ratio_serv <= limit_serv and ratio_buckling <= limit_buckling:
                return True
            else:
                return False

        else:
            return False #{"Error": "Invalid stiffener_type provided."}

    # ==========================================================================
    """    SECTION  9     MEMBER SUBJECTED TO COMBINED FORCES   """

    @staticmethod
    def cl_9_2_2_high_shear_moment(Md, Mfd, b, Ze, fy, gamma_mo):
        Mdv=Md - b(Md-Mfd)
        if Mdv <= 1.2*Ze*fy/gamma_mo:
            return Mdv
        else:
            print('Reduced elastic buckling moment error')
            return 0
    # ==========================================================================
    """   SECTION  10    CONNECTIONS    """

    # -------------------------------------------------------------
    #   10.1 General
    # -------------------------------------------------------------
    # -------------------------------------------------------------
    #   10.2 Location Details of Fasteners
    # -------------------------------------------------------------

    # cl. 10.2.1 Clearances for Holes for Fasteners

    @staticmethod
    def cl_8_7_1_3_stiff_bearing_length(shear_force, web_thickness, flange_thickness, root_radius, fy):
        #     This function returns the stiff bearing length, b1 for web local yielding and web crippling check
        #     Minimum value of b1 is not defined in IS 800, reference has been made to AISC for such cases (CL. J10-2)
        gamma_m0 = IS800_2007.cl_5_4_1_Table_5['gamma_m0']['yielding']
        bearing_length = round((float(shear_force) * 1000) * gamma_m0 / web_thickness / fy, 3)
        b1_req = bearing_length - (flange_thickness + root_radius)
        k = flange_thickness + root_radius
        b1 = max(b1_req, k)
        return b1

    # ==========================================================================
    """    SECTION  9     MEMBER SUBJECTED TO COMBINED FORCES   """

    # -------------------------------------------------------------
    #   10.1 General
    # -------------------------------------------------------------






    # ==========================================================================
    """   SECTION  10    CONNECTIONS    """

    # -------------------------------------------------------------
    #   10.1 General
    # -------------------------------------------------------------
    # -------------------------------------------------------------
    #   10.2 Location Details of Fasteners
    # -------------------------------------------------------------

    # cl. 10.2.1 Clearances for Holes for Fasteners
    @staticmethod
    def cl_10_2_1_bolt_hole_size(d, bolt_hole_type='Standard'):
        """Calculate bolt hole diameter as per Table 19 of IS 800:2007
        Args:
             d - Nominal diameter of fastener in mm (float)
             bolt_hole_type - Either 'Standard' or 'Over-sized' or 'short_slot' or 'long_slot' (str)
        Returns:
            bolt_hole_size -  Diameter of the bolt hole in mm (float)
        Note:
            Reference:
            IS 800, Table 19 (Cl 10.2.1)
        TODO:ADD KEY_DISP for for Standard/oversize etc and replace these strings
        """
        table_19 = {
            "12-14": {'Standard': 1.0, 'Over-sized': 3.0, 'short_slot': 4.0, 'long_slot': 2.5},
            "16-22": {'Standard': 2.0, 'Over-sized': 4.0, 'short_slot': 6.0, 'long_slot': 2.5},
            "24": {'Standard': 2.0, 'Over-sized': 6.0, 'short_slot': 8.0, 'long_slot': 2.5},
            "24+": {'Standard': 3.0, 'Over-sized': 8.0, 'short_slot': 10.0, 'long_slot': 2.5}
        }
        import re
        # d = str(re.sub("[^0-9]", "", str(d)))
        d = int(d)

        if d < 12:
            clearance = 0
        elif d <= 14:
            clearance = table_19["12-14"][bolt_hole_type]
        elif d <= 22:
            clearance = table_19["16-22"][bolt_hole_type]
        elif d <= 24:
            clearance = table_19["24"][bolt_hole_type]
        else:
            clearance = table_19["24+"][bolt_hole_type]
        if bolt_hole_type == 'long_slot':
            bolt_hole_size = (clearance + 1) * d
        else:
            bolt_hole_size = clearance + d
        return bolt_hole_size

    # cl. 10.2.2 Minimum Spacing
    @staticmethod
    def cl_10_2_2_min_spacing(d):
        """Calculate minimum distance between centre of fasteners
        Args:
             d - Nominal diameter of fastener in mm (float)
        Returns:
            Minimum distance between centre of fasteners in mm (float)
        Note:
            Reference:
            IS 800:2007, cl. 10.2.2
        """
        return 2.5 * d

    # cl. 10.2.3.1 Maximum Spacing
    @staticmethod
    def cl_10_2_3_1_max_spacing(plate_thicknesses):
        """Calculate maximum distance between centre of fasteners
        Args:
             plate_thicknesses- List of thicknesses in mm of connected plates (list or tuple)
        Returns:
            Maximum distance between centres of adjacent fasteners in mm (float)
        Note:
            Reference:
            IS 800:2007, cl. 10.2.3.1
        """
        # print(plate_thicknesses)
        t = min(plate_thicknesses)
        return min(32 * t, 300.0)

    # cl. 10.2.3.2 Maximum pitch in tension and compression members
    @staticmethod
    def cl_10_2_3_2_max_pitch_tension_compression(d, plate_thicknesses, member_type):
        """Calculate maximum pitch between centre of fasteners lying in the direction of stress
        Args:
             d - Nominal diameter of fastener in mm (float)
             plate_thicknesses - List of thicknesses in mm of connected plates (list or tuple)
             member_type - Either 'tension' or 'compression' or 'compression_butting' (str)
        Returns:
            Maximum distance between centres of adjacent fasteners in mm (float)
        Note:
            Reference:
            IS 800:2007, cl. 10.2.3.2
        """
        t = min(plate_thicknesses)
        if member_type == 'tension':
            return min(16 * t, 200.0)
        elif member_type == 'compression':
            return min(12 * t, 200.0)
        else:
            # TODO compression members wherein forces are transferred through butting faces is given in else
            return 4.5 * d

    # cl. 10.2.4.2  Minimum Edge and End Distances
    @staticmethod
    def cl_10_2_4_2_min_edge_end_dist(d, bolt_hole_type='Standard', edge_type='Sheared or hand flame cut'):
        """Calculate minimum end and edge distance
        Args:
             d - Nominal diameter of fastener in mm (float)
             edge_type - Either 'hand_flame_cut' or 'machine_flame_cut' (str)
        Returns:
                Minimum edge and end distances from the centre of any hole to the nearest edge of a plate in mm (float)
        Note:
            Reference:
            IS 800:2007, cl. 10.2.4.2
        """

        d_0 = IS800_2007.cl_10_2_1_bolt_hole_size(d, bolt_hole_type)
        if edge_type == 'Sheared or hand flame cut':
            return 1.7 * d_0
        else:
            # TODO : bolt_hole_type == 'machine_flame_cut' is given in else
            return 1.5 * d_0

    # cl. 10.2.4.3  Maximum Edge Distance
    @staticmethod
    def cl_10_2_4_3_max_edge_dist(conn_plates_t_fu_fy, corrosive_influences=False):
        """Calculate maximum end and edge distance
        Args:
             conn_plates_t_fu_fy - List of tuples with plate thicknesses in mm, fu in MPa, fy in MPa (list of tuples)
                                example:- [ (12, 410, 250), (10, 440, 300) ]
             corrosive_influences - Whether the members are exposed to corrosive influences or not (Boolean)
        Returns:
            Maximum edge distance to the nearest line of fasteners from an edge of any un-stiffened part in mm (float)
        Note:
            Reference:
            IS 800:2007, cl. 10.2.4.3
        """
        # TODO : Differentiate outer plates and connected plates.
        t_epsilon_considered = conn_plates_t_fu_fy[0][0] * math.sqrt(250 / float(conn_plates_t_fu_fy[0][2]))
        t_considered = conn_plates_t_fu_fy[0][0]
        t_min = t_considered
        for i in conn_plates_t_fu_fy:
            t = i[0]
            f_y = i[2]
            if f_y > 0:
                epsilon = math.sqrt(250 / f_y)
                if t * epsilon <= t_epsilon_considered:
                    t_epsilon_considered = t * epsilon
                    t_considered = t
                if t < t_min:
                    t_min = t

         # epsilon = math.sqrt(250 / f_y)

        if corrosive_influences is True:
            return 40.0 + (4 * t_min)
        else:
            return 12 * t_epsilon_considered

    # -------------------------------------------------------------
    #   10.3 Bearing Type Bolts
    # -------------------------------------------------------------

    # cl. 10.3.2 Design strength of bearing type bolt
    @staticmethod
    def cl_10_3_2_bolt_design_strength(V_dsb, V_dpb):
        """Calculate design strength of bearing type bolt
        Args:
            V_dsb - Design shear strength of bearing bolt in N (float)
            V_dpb - Design bearing strength of bolt on the plate in N (float)
        Returns:
            V_db - Design strength of bearing bolt in N (float)
        Note:
            Reference:
            IS 800:2007,  cl 10.3.2
        """
        V_db = min(V_dsb, V_dpb)
        return V_db

    # cl. 10.3.3 Shear Capacity of Bearing Bolt

    @staticmethod
    def cl_10_3_3_bolt_shear_capacity(f_ub, A_nb, A_sb, n_n, n_s=0, safety_factor_parameter=None):
        """Calculate design shear strength of bearing bolt
        Args:
            f_ub - Ultimate tensile strength of the bolt in MPa (float)
            A_nb - Net shear area of the bolt at threads in sq. mm  (float)
            A_sb - Nominal plain shank area of the bolt in sq. mm  (float)
            n_n - Number of shear planes with threads intercepting the shear plane (int)
            n_s -  Number of shear planes without threads intercepting the shear plane (int)
            safety_factor_parameter - Either 'field' or 'shop' (str)
        return:
            V_dsb - Design shear strength of bearing bolt in N (float)
        Note:
            Reference:
            IS 800:2007,  cl 10.3.3
        """
        V_nsb = f_ub / math.sqrt(3) * (n_n * A_nb + n_s * A_sb)
        gamma_mb = IS800_2007.cl_5_4_1_Table_5['gamma_mb'][KEY_DP_FAB_SHOP]
        V_dsb = V_nsb / gamma_mb
        return V_dsb

    # cl. 10.3.3.1 Long joints
    @staticmethod
    def cl_10_3_3_1_bolt_long_joint(d, l_j):
        """ Calculate reduction factor for long joints.
        Args:
            l_j = Length of joint of a splice or end connection as defined in cl. 10.3.3.1 (float)
            d = Nominal diameter of the fastener (float)
        Return:
            beta_lj  = Reduction factor for long joints (float)
        Note:
            Reference:
            IS 800:2007,  cl 10.3.3.1
        """
        beta_lj = 1.075 - 0.005 * l_j / d
        if beta_lj <= 0.75:
            beta_lj = 0.75
        elif beta_lj >= 1.0:
            beta_lj = 1.0
        if l_j >= 15.0 * d:
            return beta_lj
        else:
            return 1.0

    # 10.3.3.2 Large grip lengths
    @staticmethod
    def cl_10_3_3_2_bolt_large_grip(d, l_g, l_j=0.0):
        """ Calculate reduction factor for large grip lengths.
        Args:
            l_g = Grip length equal to the total thickness of the connected plates as defined in cl. 10.3.3.2 (float)
            d = Nominal diameter of the fastener (float)
        Return:
            beta_lg = Reduction factor for large grip lengths (float) if applicable
        Note:
            Reference:
            IS 800:2007,  cl 10.3.3.2
        """
        beta_lg = 8.0 / (3.0 + l_g / d)
        if l_j != 0.0:
            if beta_lg >= IS800_2007.cl_10_3_3_1_bolt_long_joint(d, l_j):
                beta_lg = IS800_2007.cl_10_3_3_1_bolt_long_joint(d, l_j)
        else:
            pass
        if l_g <= 5.0 * d:
            beta_lg = 1.0
        # TODO: Check the maximum limit of 8d in each individual modules
        # elif l_g > 8.0 * d:
        #     return "GRIP LENGTH TOO LARGE"
        return round(beta_lg,2)

    # 10.3.3.3 Packing Plates
    @staticmethod
    def cl_10_3_3_3_packing_plates(t=0.0):
        """ Calculate reduction factor for packing plates.
        Args:
            t = thickness of the thickest packing plate, in mm
        Return:
            beta_pk = Reduction factor for packing plates (float) if applicable
        Note:
            Reference:
            IS 800:2007,  cl 10.3.3.3
        """
        if t > 6.0:
            beta_pk = (1.0 - 0.0125 * t)
        else:
            beta_pk = 1.0
        return beta_pk

    # cl. 10.3.4 Bearing Capacity of the Bolt
    @staticmethod
    def cl_10_3_4_bolt_bearing_capacity(f_u, f_ub, t, d, e, p, bolt_hole_type='Standard',
                                        safety_factor_parameter=KEY_DP_FAB_FIELD):

        """Calculate design bearing strength of a bolt on any plate.
        Args:
            f_u     - Ultimate tensile strength of the plate in MPa (float)
            f_ub    - Ultimate tensile strength of the bolt in MPa (float)
            t       - Summation of thicknesses of the connected plates in mm as defined in cl. 10.3.4 (float)
            d       - Diameter of the bolt in mm (float)
            e       - End distance of the fastener along bearing direction in mm (float)
            p       - Pitch distance of the fastener along bearing direction in mm (float)
            bolt_hole_type - Either 'Standard' or 'Over-sized' or 'short_slot' or 'long_slot' (str)
            safety_factor_parameter - Either 'Field' or 'Shop' (str)
        return:
            V_dpb - Design bearing strength of bearing bolt in N (float)
        Note:
            Reference:
            IS 800:2007,  cl 10.3.4
        """
        d_0 = IS800_2007.cl_10_2_1_bolt_hole_size(d, bolt_hole_type)

        if p > 0.0:
            k_b = min(e / (3.0 * d_0), p / (3.0 * d_0) - 0.25, f_ub / f_u, 1.0)
        else:
            k_b = min(e / (3.0 * d_0), f_ub / f_u, 1.0)  # calculate k_b when there is no pitch (p = 0)

        k_b = round(k_b, 2)
        V_npb = 2.5 * k_b * d * t * f_u
        gamma_mb = IS800_2007.cl_5_4_1_Table_5['gamma_mb'][safety_factor_parameter]
        V_dpb = V_npb / gamma_mb

        if bolt_hole_type == 'Over-sized' or bolt_hole_type == 'short_slot':
            V_dpb *= 0.7
        elif bolt_hole_type == 'long_slot':
            V_dpb *= 0.5

        return V_dpb

    @staticmethod
    def cl_10_3_5_bearing_bolt_tension_resistance(f_ub, f_yb, A_sb, A_n, safety_factor_parameter=KEY_DP_FAB_FIELD):
        """Calculate design tensile strength of bearing bolt
        Args:
            f_ub - Ultimate tensile strength of the bolt in MPa (float)
            f_yb - Yield strength of the bolt in MPa (float)
            A_sb - Shank area of bolt in sq. mm  (float)
            A_n - Net tensile stress area of the bolts as per IS 1367 in sq. mm  (float)
        return:
            T_db - Design tensile strength of bearing bolt in N (float)
        Note:
            Reference:
            IS 800:2007,  cl 10.3.5
        """
        gamma_mb = IS800_2007.cl_5_4_1_Table_5['gamma_mb'][safety_factor_parameter]
        gamma_m0 = IS800_2007.cl_5_4_1_Table_5['gamma_m0']['yielding']
        T_nb = min(0.90 * f_ub * A_n, f_yb * A_sb * gamma_mb / gamma_m0)
        return T_nb / gamma_mb

        # cl. 10.3.6 Bolt subjected to combined shear and tension of bearing bolts

    @staticmethod
    def cl_10_3_6_bearing_bolt_combined_shear_and_tension(V_sb, V_db, T_b, T_db):
        """Check for bolt subjected to combined shear and tension
        Args:
            V_sb - factored shear force acting on the bolt,
            V_db - design shear capacity,
            T_b - factored tensile force acting on the bolt,
            T_db - design tension capacity.
        return: combined shear and friction value
        Note:
            Reference:
            IS 800:2007,  cl 10.3.6
        """
        return (V_sb / V_db) ** 2 + (T_b / T_db) ** 2

    # -------------------------------------------------------------
    #   10.4 Friction Grip Type Bolting
    # -------------------------------------------------------------

    # cl. 10.4.3 Slip Resistance
    @staticmethod
    def cl_10_4_3_bolt_slip_resistance(f_ub, A_nb, n_e, mu_f, bolt_hole_type='Standard', slip_resistance='ultimate_load'):
        # TODO : Ensure default slip_resistance = 'service_load' or 'ultimate_load'
        """Calculate design shear strength of friction grip bolt as governed by slip
        Args:
            f_ub - Ultimate tensile strength of the bolt in MPa (float)
            A_nb - Net area of the bolt at threads in sq. mm  (float)
            n_e - Number of  effective interfaces offering  frictional resistance to slip (int)
            mu_f - coefficient of friction (slip factor) as specified in Table 20
            bolt_hole_type - Either 'Standard' or 'Over-sized' or 'short_slot' or 'long_slot' (str)
            slip_resistance - whether slip resistance is required at service load or ultimate load
                              Either 'service_load' or 'ultimate_load' (str)
        return:
            V_dsf - Design shear strength of friction grip bolt as governed by slip in N (float)
        Note:
            Reference:
            IS 800:2007,  cl 10.4.3
            AMENDMENT NO. 1 (JANUARY 2012) to IS 800:2007
        """
        f_0 = 0.70 * f_ub
        F_0 = A_nb * f_0
        if slip_resistance == 'service_load':
            gamma_mf = 1.10
        else:
            # TODO : slip _resistance for 'ultimate_load' is given in else
            gamma_mf = 1.25
        if bolt_hole_type == 'Standard':
            K_h = 1.0
        elif bolt_hole_type == 'Over-sized' or bolt_hole_type == 'short_slot' or bolt_hole_type == 'long_slot':
            K_h = 0.85
        else:
            # TODO : long_slot bolt loaded parallel to slot is given in else
            K_h = 0.7
        if mu_f >= 0.55:
            mu_f = 0.55
        V_nsf = mu_f * n_e * K_h * F_0
        V_dsf = V_nsf / gamma_mf
        return V_dsf, K_h, gamma_mf

    # Table 20 Typical Average Values for Coefficient of Friction, mu_f (list)
    cl_10_4_3_Table_20 = [0.20, 0.50, 0.10, 0.25, 0.30, 0.52, 0.30, 0.30, 0.50, 0.33, 0.48, 0.1]

    # cl. 10.4.5 Tension Resistance
    @staticmethod
    def cl_10_4_5_friction_bolt_tension_resistance(f_ub, f_yb, A_sb, A_n,
                                                   safety_factor_parameter=KEY_DP_FAB_FIELD):
        """Calculate design tensile strength of friction grip bolt
        Args:
            f_ub - Ultimate tensile strength of the bolt in MPa (float)
            f_yb - Yield strength of the bolt in MPa (float)
            A_sb - Shank area of bolt in sq. mm  (float)
            A_n - Net tensile stress area of the bolts as per IS 1367 in sq. mm  (float)
        return:
            T_df - Design tensile strength of friction grip bolt in N (float)
        Note:
            Reference:
            IS 800:2007,  cl 10.4.5
            AMENDMENT NO. 1 (JANUARY 2012) to IS 800:2007
        """
        gamma_mf = IS800_2007.cl_5_4_1_Table_5['gamma_mf'][safety_factor_parameter]
        gamma_m0 = IS800_2007.cl_5_4_1_Table_5['gamma_m0']['yielding']
        gamma_m1 = IS800_2007.cl_5_4_1_Table_5['gamma_m1']['ultimate_stress']

        T_nf = min(0.9 * f_ub * A_n, f_yb * A_sb * gamma_m1 / gamma_m0)
        return T_nf / gamma_mf

    # cl. 10.4.6 Combined shear and Tension for friction grip bolts
    @staticmethod
    def cl_10_4_6_friction_bolt_combined_shear_and_tension(V_sf, V_df, T_f, T_df):
        """Calculate combined shear and tension of friction grip bolt
                Args:
                   V_sf - applied factored shear at design load
                   V_df - design shear strength
                   T_f - externally applied factored tension at design load
                   T_df - design tension strength
                return:
                    combined shear and friction value
                Note:
                    Reference:
                    IS 800:2007,  cl 10.4.6
        """
        return (V_sf / V_df) ** 2 + (T_f / T_df) ** 2

    @staticmethod
    def cl_10_4_7_bolt_prying_force(T_e, l_v, f_o, b_e, t, f_y, end_dist, pre_tensioned='', eta=1.5):
        """Calculate prying force of friction grip bolt
                       Args:
                          2 * T_e - Force in 2 bolts on either sides of the web/plate
                          l_v - distance from the bolt centre line to the toe of the fillet weld or to half
                                the root radius for a rolled section,
                          beta - 2 for non pre-tensioned bolt and 1 for pre-tensioned bolt
                          eta - 1.5
                          b_e - effective width of flange per pair of bolts
                          f_o - proof stress in consistent units
                          t - thickness of the end plate
                       return:
                           Prying force of friction grip bolt
                       Note:
                           Reference:
                           IS 800:2007,  cl 10.4.7
        """
        if pre_tensioned == 'Pre-tensioned':
            beta = 1
        else:
            beta = 2

        le_1 = end_dist
        le_2 = (1.1 * t) * math.sqrt((beta * f_o) / f_y)  # here f_o is taken as N/mm^2
        l_e = min(le_1, le_2)

        # # Note: In the below equation of Q, f_o is taken as kN since the value of T_e is in kN
        # Q = (l_v / (2 * l_e)) * (T_e - ((beta * eta * f_o * b_e * 1e-3 * t ** 4) / (27 * l_e * l_v ** 2)))  # kN

        # All Calculations are in N-mm. Please pass arguments accordingly.
        Q = (l_v / (2 * l_e)) * (T_e - ((beta * eta * f_o * b_e * t ** 4) / (27 * l_e * l_v ** 2)))  # N

        if Q < 0:
            Q = 0.0

        return round(Q, 2)  # N

    # -------------------------------------------------------------
    #   10.5 Welds and Welding
    # -------------------------------------------------------------

    # cl. 10.5.2.3 Minimum Size of First Run or of a Single Run Fillet Weld
    @staticmethod
    def cl_10_5_2_3_min_weld_size(part1_thickness, part2_thickness):
        """Calculate minimum size of fillet weld as per Table 21 of IS 800:2007
        Args:
            part1_thickness - Thickness of either plate element being welded in mm (float)
            part2_thickness - Thickness of other plate element being welded in mm (float)
        Returns:
            min_weld_size - Minimum size of first run or of a single run fillet weld in mm (float)
        Note:
            Reference:
            IS 800, Table 21 (Cl 10.5.2.3) : Minimum Size of First Run or of a Single Run Fillet Weld
        """
        thicker_part_thickness = max(part1_thickness, part2_thickness)
        thinner_part_thickness = min(part1_thickness, part2_thickness)

        if thicker_part_thickness <= 10.0:
            min_weld_size = 3
        elif thicker_part_thickness <= 20.0:
            min_weld_size = 5
        elif thicker_part_thickness <= 32.0:
            min_weld_size = 6
        else:  # thicker_part_thickness <= 50.0:
            min_weld_size = 10
        # TODO else:
        if min_weld_size > thinner_part_thickness:
            min_weld_size = thinner_part_thickness
        return min_weld_size

    @staticmethod
    def cl_10_5_3_1_max_weld_throat_thickness(part1_thickness, part2_thickness, special_circumstance=False):

        """Calculate maximum effective throat thickness of fillet weld
        Args:
            part1_thickness - Thickness of either plate element being welded in mm (float)
            part2_thickness - Thickness of other plate element being welded in mm (float)
            special_circumstance - (Boolean)
        Returns:
            maximum effective throat thickness of fillet weld in mm (float)
        Note:
            Reference:
            IS 800:2007,  cl 10.5.3.1
        """

        if special_circumstance is True:
            return min(part1_thickness, part2_thickness)
        else:
            return 0.7 * min(part1_thickness, part2_thickness)

    @staticmethod
    def cl_10_5_3_2_factor_for_throat_thickness(fusion_face_angle=90):

        table_22 = {'60-90': 0.70, '91-100': 0.65, '101-106': 0.60, '107-113': 0.55, '114-120': 0.50}
        fusion_face_angle = int(round(fusion_face_angle))
        if 60 <= fusion_face_angle <= 90:
            K = table_22['60-90']
        elif 91 <= fusion_face_angle <= 100:
            K = table_22['91-100']
        elif 101 <= fusion_face_angle <= 106:
            K = table_22['101-106']
        elif 107 <= fusion_face_angle <= 113:
            K = table_22['107-113']
        elif 114 <= fusion_face_angle <= 120:
            K = table_22['114-120']
        else:
            K = "NOT DEFINED"
        try:
            K = float(K)
        except ValueError:
            return

        return K


    @staticmethod
    def cl_10_5_3_2_fillet_weld_effective_throat_thickness(fillet_size, fusion_face_angle=90):

        """Calculate effective throat thickness of fillet weld for stress calculation
        Args:
            fillet_size - Size of fillet weld in mm (float)
            fusion_face_angle - Angle between fusion faces in degrees (int)
        Returns:
            Effective throat thickness of fillet weld for stress calculation in mm (float)
        Note:
            Reference:

            IS 800:2007,  cl 10.5.3.2

        """
        K = IS800_2007.cl_10_5_3_2_factor_for_throat_thickness(fusion_face_angle)

        throat = max(round((K * fillet_size),2), 3)

        return throat

    @staticmethod
    def cl_10_5_3_2_fillet_weld_effective_throat_thickness_constant(fusion_face_angle=90):

        """Calculate effective throat thickness of fillet weld for stress calculation

        Args:
            fusion_face_angle - Angle between fusion faces in degrees (int)

        Returns:
            Effective throat thickness of fillet weld constant

        Note:
            Reference:
            IS 800:2007,  cl 10.5.3.2zzz

        """
        table_22 = {'60-90': 0.70, '91-100': 0.65, '101-106': 0.60, '107-113': 0.55, '114-120': 0.50}
        fusion_face_angle = int(round(fusion_face_angle))
        if 60 <= fusion_face_angle <= 90:
            K = table_22['60-90']
        elif 91 <= fusion_face_angle <= 100:
            K = table_22['91-100']
        elif 101 <= fusion_face_angle <= 106:
            K = table_22['101-106']
        elif 107 <= fusion_face_angle <= 113:
            K = table_22['107-113']
        elif 114 <= fusion_face_angle <= 120:
            K = table_22['114-120']
        else:
            K = "NOT DEFINED"
        try:
            K = float(K)
        except ValueError:
            return

        return K

        # Cl. 10.5.3.3 Effective throat size of groove (butt) welds

    @staticmethod
    def cl_10_5_3_3_groove_weld_effective_throat_thickness(*args):

        """Calculate effective throat thickness of complete penetration butt welds
        *args:
            Thicknesses of each plate element being welded in mm (tuple of float)
        Returns:
            Effective throat thickness of CJP butt weld in mm (float)
        Note:
            Reference:
            IS 800:2007,  cl 10.5.3.3
        """
        return min(*args)

    @staticmethod
    def cl_10_5_4_1_fillet_weld_effective_length(fillet_size, available_length):

        """Calculate effective length of fillet weld from available length to weld in practice
        Args:
            #fillet_size - Size of fillet weld in mm (float)
            available_length - Available length in mm to weld the plates in practice (float)
        Returns:
            Effective length of fillet weld in mm (float)
        Note:
            Reference:
            IS 800:2007,  cl 10.5.4.1
        """
        if available_length <= 4 * fillet_size:
            effective_length = 0
        else:
            effective_length = available_length - 2 * fillet_size
        return effective_length

    # cl. 10.5.7.1.1 Design stresses in fillet welds
    @staticmethod
    def cl_10_5_7_1_1_fillet_weld_design_stress(ultimate_stresses, fabrication=KEY_DP_FAB_SHOP):

        """Calculate the design strength of fillet weld
        Args:
            ultimate_stresses - Ultimate stresses of weld and parent metal in MPa (list or tuple)
            fabrication - Either 'shop' or 'field' (str)
        Returns:
            Design strength of fillet weld in MPa (float)
        Note:
            Reference:
            IS 800:2007,  cl 10.5.7.1.1
        """
        f_u = min(ultimate_stresses)
        f_wn = (f_u / math.sqrt(3))
        gamma_mw = IS800_2007.cl_5_4_1_Table_5['gamma_mw'][fabrication]
        f_wd = f_wn / gamma_mw
        return f_wd

    # cl. 10.5.7.3 Long joints
    @staticmethod
    def cl_10_5_7_3_weld_long_joint(l_j, t_t):

        """Calculate the reduction factor for long joints in welds
        Args:
            l_j - length of joints in the direction of force transfer in mm (float)
            t_t - throat size of the weld in mm (float)
        Returns:
             Reduction factor, beta_lw for long joints in welds (float)
        Note:
            Reference:
            IS 800:2007,  cl 10.5.7.3
        """
        if l_j <= 150 * t_t:
            return 1.0
        beta_lw = 1.2 - ((0.2 * l_j) / (150 * t_t))
        if beta_lw >= 1.0:
            beta_lw = 1.0
        elif beta_lw <= 0.6:
            beta_lw = 0.6
        return beta_lw


    # -------------------------------------------------------------
    #   10.6 Design of Connections
    # -------------------------------------------------------------
    # -------------------------------------------------------------
    #   10.7 Minimum Design Action on Connection
    # -------------------------------------------------------------
    # -------------------------------------------------------------
    #   10.8 Intersections
    # -------------------------------------------------------------
    # -------------------------------------------------------------
    #   10.9 Choice of Fasteners
    # -------------------------------------------------------------
    # -------------------------------------------------------------
    #   10.10 Connection Components
    # -------------------------------------------------------------
    # -------------------------------------------------------------
    #   10.11 Analysis of a Bolt/Weld Group
    # -------------------------------------------------------------
    # -------------------------------------------------------------
    #   10.12 Lug Angles
    # -------------------------------------------------------------
    # -------------------------------------------------------------
    # ==========================================================================
    """    SECTION  11    WORKING STRESS DESIGN   """
    # ==========================================================================
    """    SECTION  12    DESIGN AND DETAILING FOR EARTHQUAKE   """
    # ==========================================================================
    """    SECTION  13    FATIGUE   """
    # ==========================================================================
    """    SECTION  14    DESIGN ASSISTED BY TESTING   """
    # ==========================================================================
    """    SECTION  15    DURABILITY   """
    # ==========================================================================
    """    SECTION  16    FIRE RESISTANCE   """
    # ==========================================================================
    """    SECTION  17    FABRICATION AND ERECTION   """
    # ==========================================================================
    """    ANNEX  A       LIST OF REFERRED INDIAN STANDARDS   """
    # ==========================================================================
    """    ANNEX  B       ANALYSIS AND DESIGN METHODS   """
    # ==========================================================================
    """    ANNEX  C       DESIGN AGAINST FLOOR VIBRATION   """
    # ==========================================================================
    """    ANNEX  D       DETERMINATION OF EFFECTIVE LENGTH OF COLUMNS   """
    # ==========================================================================
    """    ANNEX  E       ELASTIC LATERAL TORSIONAL BUCKLING   """
    # ==========================================================================
    """    ANNEX  F       CONNECTIONS   """
    # ==========================================================================
    """    ANNEX  G       GENERAL RECOMMENDATIONS FOR STEELWORK TENDERS AND CONTRACTS   """
    # ==========================================================================
    """    ANNEX  H       PLASTIC PROPERTIES OF BEAMS   """
    # ==========================================================================
    """     ------------------END------------------     """
    