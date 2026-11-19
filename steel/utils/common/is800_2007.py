"""Steel design helpers for review against BIS CED 07 (27869) WC, April 2025.
Units: N, mm, MPa, N mm. This is an educational draft implementation.
Adapted from the IS 800:2007 project module by ajmalbabums (2018).
See the migration register for supported inputs and unresolved provisions.
"""
import math


def _positive(*values):
    if any(v is None or not math.isfinite(v) or v <= 0 for v in values):
        raise ValueError("Expected finite positive dimensions or properties")


def _classify(ratio, limits, scale):
    _positive(ratio, scale)
    for label, limit in zip(("Plastic", "Compact", "Semi-Compact"), limits):
        if limit is not None and ratio <= limit * scale:
            return label
    return "Slender"


class IS800_2025_Draft:
    """Calculations for the April 2025 wide circulation draft, using N, mm and MPa."""

    # Draft Table 5, clause 12.4.1. Strength factors also used by the retained project calls.
    material_factors = {
        "gamma_m0": {"yielding": 1.10, "buckling": 1.10},
        "gamma_m1": {"ultimate_stress": 1.25},
        "gamma_mb": {"Shop": 1.25, "Field": 1.25},
        "gamma_mf": {"Shop": 1.25, "Field": 1.25},
        "gamma_mr": {"Shop": 1.25, "Field": 1.25},
        "gamma_mw": {"Shop": 1.25, "Field": 1.50},
    }
    # Surface treatment row i-xii of 17.4.3, Table 20.
    slip_factors = (0.20, 0.50, 0.10, 0.25, 0.30, 0.52, 0.30, 0.30, 0.50, 0.33, 0.48, 0.10)

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

    @staticmethod
    def bearing_pressure(fck_concrete, fck_bedding, pedestal_area, base_contact_area):
        """14.4.1. Concrete and bedding characteristic cube strengths in MPa."""
        _positive(fck_concrete, fck_bedding, pedestal_area, base_contact_area)
        fck = min(fck_concrete, fck_bedding)
        return min(0.45 * math.sqrt(pedestal_area/base_contact_area), 0.9) * fck

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

    @staticmethod
    def imperfection_factor(curve):
        """Table 7. Column imperfection factor."""
        return {"a0": 0.13, "a": 0.21, "b": 0.34, "c": 0.49, "d": 0.76}[curve]

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
    def ltb_design_stress(chi_lt, fy):
        """15.2.2. Beam bending compressive stress in MPa."""
        _positive(chi_lt, fy)
        if chi_lt > 1:
            raise ValueError("chi_LT exceeds unity")
        return chi_lt*fy/1.1

    @staticmethod
    def cl_8_2_2_Unsupported_beam_bending_compressive_stress(X_lt, fy, gamma_mo):
        return X_lt * fy / gamma_mo

    @staticmethod
    def ltb_reduction(lambda_lt, lambda_y, alpha_lt, fm):
        """15.2.2, doubly symmetric beam with lateral support at ends.
        Supply dimensionless alpha_lt and fm for the applicable Tables 13 & 14 rows.
        Returns (phi_LT, chi_LT)."""
        _positive(lambda_lt, lambda_y, alpha_lt, fm)
        phi = .5*(1 + fm*((lambda_lt/lambda_y)**2*alpha_lt*(lambda_lt-.2) + lambda_lt**2))
        root = phi**2 - fm*lambda_lt**2
        if root < 0:
            raise ValueError("Non-real reduction factor; check inputs and draft equation")
        return phi, min(1, fm/(phi+math.sqrt(root)))

    @staticmethod
    def ltb_elastic_moment(E, G, iy, it, iw, length):
        """15.2.2.1 simply supported prismatic symmetric section, Mcr in N mm."""
        _positive(E, G, iy, it, length)
        if iw < 0:
            raise ValueError("Warping constant must be nonnegative")
        k = math.pi**2*E/length**2
        return math.sqrt(k*iy*(G*it+k*iw))

    @staticmethod
    def rolled_beam_fcrb(E, length_over_ry, hf_over_tf):
        """15.2.2.1 approximation for a non-slender rolled section, in MPa."""
        _positive(E, length_over_ry, hf_over_tf)
        return (1.1*math.pi**2*E / length_over_ry**2
                * math.sqrt(1 + (length_over_ry/hf_over_tf)**2/20))

    @staticmethod
    def ltb_slenderness(beta_b, zp, ze, fy, mcr):
        """15.2.2. Dimensionless slenderness from elastic critical moment in N mm."""
        _positive(beta_b, zp, ze, fy, mcr)
        return math.sqrt(min(beta_b*zp,1.2*ze)*fy/mcr)

    @staticmethod
    def cl_8_2_2_1_elastic_buckling_moment_fcrb( fy, fcrb=0):

        return math.sqrt(fy/fcrb)

    @staticmethod
    def simple_beam_ltb_length(row, length, depth, *, loading):
        """15.3.1, Table 15 rows i-vii. Effective length in mm."""
        _positive(length, depth)
        if row not in range(1, 8):
            raise ValueError("Table 15 row must be 1 to 7")
        factors = {"normal": (.70,.75,.80,.85,1,1,1.2),
                   "destabilizing": (.85,.90,.95,1,1.2,1.2,1.4)}[loading]
        return factors[row-1]*length + (2*depth if row >= 6 else 0)

    @staticmethod
    def cantilever_ltb_length(length, support_row, top_row, *, loading):
        """15.3.3, Table 16. Support a-d and top i-iv numbered 1-4."""
        _positive(length)
        if support_row not in range(1,5) or top_row not in range(1,5):
            raise ValueError("Table 16 row outside 1-4")
        factors = {
            "normal": ((3,2.7,2.4,2.1),(2,1.8,1.6,1.4),(1,.9,.8,.7),(.8,.7,.6,.5)),
            "destabilizing": ((7.5,7.5,4.5,3.6),(5,5,3,2.4),(2.5,2.5,1.5,1.2),(1.4,1.4,.6,.5)),
        }
        return length*factors[loading][support_row-1][top_row-1]

    @staticmethod
    def design_shear_yield(av, fy):
        """15.4.1. Design shear resistance in N where shear yielding governs."""
        _positive(av, fy)
        return av*fy/(math.sqrt(3)*1.1)

    @staticmethod
    def cl_8_4_design_shear_strength(A_vg, f_y):
        """Draft 15.4.1. Retained project calculation and units."""
        gamma_m0 = IS800_2025_Draft.material_factors["gamma_m0"]['yielding']
        V_d = ((A_vg * f_y) / (math.sqrt(3) * gamma_m0))  # N

        return V_d

    @staticmethod
    def cl_8_4_2_1_web_buckling_stiff(d, tw, e,type = 1, kv = None):
        """Draft 15.4.2.1. Retained project calculation and units."""
        d_tw = d / tw
        if type == 1 and d_tw <= 67 * e:
            return False
        elif type == 2 and d_tw <= 67 * e * math.sqrt(kv/5.35):
            return False
        return True

    @staticmethod
    def postcritical_shear(d, tw, fyw, E, nu, *, spacing=None):
        """15.4.2.2(a). I-girder with transverse stiffeners at supports.
        Returns nominal shear stress tau_b (MPa). Multiply by Av for nominal N.
        """
        _positive(d, tw, fyw, E)
        if not -1 < nu < .5:
            raise ValueError("Invalid Poisson ratio")
        kv = 5.35
        if spacing is not None:
            _positive(spacing)
            aspect = spacing/d
            kv = 4 + 5.35/aspect**2 if aspect < 1 else 5.35 + 4/aspect**2
        tau_cr = kv*math.pi**2*E/(12*(1-nu**2)*(d/tw)**2)
        tau_y = fyw/math.sqrt(3)
        slender = math.sqrt(tau_y/tau_cr)
        if slender <= .8:
            return tau_y
        if slender < 1.2:
            return (1-.8*(slender-.8))*tau_y
        return tau_y/slender**2

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
    def tension_field(d, c, tw, fyw, av, tau_b, vp, compression_flange, tension_flange):
        """15.4.2.2(b). Anchored interior panel, stiffeners at supports and panel ends.
        Each flange tuple is (width mm, thickness mm, fy MPa, axial force N).
        vp is nominal plastic shear resistance in N. Result is nominal N.
        """
        _positive(d, c, tw, fyw, av, tau_b, vp)
        if c < d:
            raise ValueError("Tension-field method requires c/d >= 1")
        phi = math.atan(d/c)/1.5
        sine = math.sin(phi)
        def anchorage(flange):
            b, t, fy, force = flange
            _positive(b, t, fy)
            utilisation = abs(force)/(b*t*fy/1.1)
            if not utilisation <= 1:
                raise ValueError("Flange force exceeds axial capacity")
            mfr = .25*b*t*t*fy*(1-utilisation**2)
            return min(c, 2*math.sqrt(mfr/(fyw*tw))/sine)
        width = d*math.cos(phi) - (c-anchorage(compression_flange)-anchorage(tension_flange))*sine
        psi = 1.5*tau_b*math.sin(2*phi)
        fv = math.sqrt(fyw**2-3*tau_b**2+psi**2) - psi
        return min(vp, av*tau_b + .9*width*tw*fv*sine)

    @staticmethod
    def cl_8_4_2_2_Mfr_TensionField(bf, tf, fyf, Nf, gamma_mo):
        """Draft 15.4.2.2(b). Retained project calculation and units."""

        M_fr = 0.25 * bf * tf ** 2 * fyf * (1 - (Nf / (bf * tf * fyf / gamma_mo)) ** 2)
        return  M_fr

    @staticmethod
    def end_panel_anchor_forces(d, tw, fy, vcr, vtf, v):
        """15.5.3. Return Rtf (N) and Mtf (N mm) for tension field anchorage.
        Use forces on a consistent basis. End stiffener and end post checks are separate.
        """
        _positive(d, tw, fy, vcr, vtf, v)
        vp = d*tw*fy/math.sqrt(3)
        if not vcr <= v <= vtf or not vcr <= vp:
            raise ValueError("Check range of tension field forces")
        hq = 1.25*vp*math.sqrt(1-vcr/vp)
        if v < vtf:
            hq *= (v-vcr)/(vtf-vcr)
        return hq/2, hq*d/10

    @staticmethod
    def web_thickness_ok(d, tw, fyw, fyf, *, stiffening, spacing=None, edges=2):
        """15.6.1.1-2. Check serviceability and compression flange buckling."""
        _positive(d, tw, fyw, fyf)
        eps_w, eps_f = math.sqrt(250/fyw), math.sqrt(250/fyf)
        if edges not in (1, 2):
            raise ValueError("edges must be 1 or 2")
        if stiffening != "none":
            if edges != 2 or spacing is None:
                raise ValueError("Stiffened rows require both edges connected and spacing")
            _positive(spacing)
        if stiffening == "none" or (stiffening == "transverse" and spacing > 3*d):
            sv = (200 if edges == 2 else 90)*eps_w
            return d/tw <= min(sv, 345*eps_f**2)
        buckling = 345*(eps_f**2 if spacing >= 1.5*d else eps_f)
        ratio = d/tw
        if stiffening == "two-longitudinal":
            sv = 400*eps_w
        elif stiffening in ("transverse", "one-longitudinal"):
            one = stiffening == "one-longitudinal"
            if one and (spacing > 2.4*d or spacing == .74*d):
                raise NotImplementedError("Spacing outside explicit 15.6.1.1(c) rows")
            sv = (250 if one else 200)*eps_w
            if spacing < .74*d:
                sv = (340 if one else 270)*eps_w
            elif spacing < d:
                ratio = spacing/tw
        else:
            raise ValueError("Unknown stiffener arrangement")
        return ratio <= sv and d/tw <= buckling

    @staticmethod
    def high_shear_moment(section_class, md, mfd, ze, fy, shear, design_shear):
        """16.2.2. Input magnitudes, N and N mm. Use only for 0.6Vd < V <= Vd."""
        _positive(md, ze, fy, shear, design_shear)
        if not .6 < shear/design_shear <= 1 or not 0 <= mfd <= md:
            raise ValueError("Check shear range and flange-only moment")
        if section_class == "Semi-Compact":
            return ze*fy/1.1
        if section_class not in ("Plastic", "Compact"):
            raise ValueError("Unsupported class")
        beta = (2*shear/design_shear - 1)**2
        return min(md - beta*(md-mfd), 1.2*ze*fy/1.1)

    @staticmethod
    def hole_dimensions(d, hole):
        """17.2.1 Table 19. Returns (width, length) mm for a circular hole or slot."""
        _positive(d)
        if 12 <= d <= 14:
            clear = (1,3,4)
        elif 16 <= d <= 22:
            clear = (2,4,6)
        elif d == 24:
            clear = (2,6,8)
        elif d > 24:
            clear = (3,8,10)
        else:
            raise ValueError("Diameter outside the printed Table 19 rows")
        normal, oversize, short = clear
        return {"standard": (d+normal,d+normal), "oversize": (d+oversize,d+oversize),
                "short-slot": (d+normal,d+short), "long-slot": (d+normal,3.5*d)}[hole]

    @staticmethod
    def min_spacing(d):
        """17.2.2. Centre-to-centre distance in mm."""
        _positive(d)
        return 2.5*d

    @staticmethod
    def cl_10_2_2_min_spacing(d):
        """Draft 17.2.2. Retained project calculation and units."""
        return 2.5 * d

    @staticmethod
    def max_spacing(t):
        """17.2.3.1. Thinner plate thickness and maximum spacing in mm."""
        _positive(t)
        return min(32*t,300)

    @staticmethod
    def cl_10_2_3_1_max_spacing(plate_thicknesses):
        """Draft 17.2.3.1. Retained project calculation and units."""
        # print(plate_thicknesses)
        t = min(plate_thicknesses)
        return min(32 * t, 300.0)

    @staticmethod
    def max_pitch(t, *, member, diameter=None):
        """17.2.3.2. Butting row applies within 1.5 member widths of butting faces."""
        _positive(t)
        if member == "butting":
            _positive(diameter)
            return min(4.5*diameter, 12*t, 200)
        return min({"tension":16, "compression":12}[member]*t, 200)

    @staticmethod
    def min_edge(hole_diameter, *, edge):
        """17.2.4.2. Minimum distance (mm); apply measurement rules of 17.2.4.1."""
        _positive(hole_diameter)
        factor = {"sheared":1.7, "hand-flame":1.7, "rolled":1.5,
                  "machine-flame":1.5, "sawn":1.5, "planed":1.5}[edge]
        return factor*hole_diameter

    @staticmethod
    def max_edge(thinner_outer_t, outer_fy, *, corrosive=False, thinnest_connected_t=None):
        """17.2.4.3. Unstiffened outer edge. Excludes back-to-back tension-member exception."""
        _positive(thinner_outer_t, outer_fy)
        limit = 12*thinner_outer_t*math.sqrt(250/outer_fy)
        if corrosive:
            _positive(thinnest_connected_t)
            limit = min(limit, 40+4*thinnest_connected_t)
        return limit

    @staticmethod
    def bearing_bolt_capacity(shear_resistance, bearing_resistance):
        """17.3.2. Use design resistances after applicable reductions, in N."""
        _positive(shear_resistance, bearing_resistance)
        return min(shear_resistance,bearing_resistance)

    @staticmethod
    def cl_10_3_2_bolt_design_strength(V_dsb, V_dpb):
        """Draft 17.3.2. Retained project calculation and units."""
        V_db = min(V_dsb, V_dpb)
        return V_db

    @staticmethod
    def bolt_shear(fub, anb, asb, nn, ns=0):
        """17.3.3, base design shear resistance before applicable reductions (N)."""
        _positive(fub, anb, asb)
        if min(nn,ns) < 0 or nn+ns < 1 or int(nn) != nn or int(ns) != ns:
            raise ValueError("Check shear plane counts")
        return fub*(nn*anb+ns*asb)/(math.sqrt(3)*1.25)

    @staticmethod
    def bolt_long_joint(d, length, bolt_count, *, uniform_transfer=False):
        """17.3.3.1 & 17.4.3.1. Shear capacity factor."""
        _positive(d, bolt_count)
        if length < 0 or int(bolt_count) != bolt_count:
            raise ValueError("Invalid joint length or bolt count")
        if uniform_transfer or bolt_count <= 2 or length <= 15*d:
            return 1.
        return max(.75, 1.075-.005*length/d)

    @staticmethod
    def bolt_grip_factor(d, grip, *, long_joint_factor=1):
        """17.3.3.2. Return grip factor; caller checks long joint separately."""
        _positive(d, grip)
        if grip > 8*d or not .75 <= long_joint_factor <= 1:
            raise ValueError("Check grip length and long joint factor")
        if grip <= 5*d:
            return 1.
        return min(8/(3+grip/d), long_joint_factor)

    @staticmethod
    def packing_factor(t):
        """17.3.3.3. Thickness of thicker packing in mm."""
        if not math.isfinite(t) or t < 0 or t >= 80:
            raise ValueError("Packing outside positive-factor domain")
        return 1-.0125*t if t > 6 else 1

    @staticmethod
    def bolt_bearing(fu, fub, thickness, d, d0, end, pitch, *, hole="standard"):
        """17.3.4. N. For slots use loading normal to slot and the hole width."""
        _positive(fu, fub, thickness, d, d0, end, pitch)
        kb = min(end/(3*d0), pitch/(3*d0)-.25, fub/fu, 1)
        if kb <= 0:
            raise ValueError("Invalid bearing geometry")
        factor = {"standard": 1, "oversize": .7, "short-slot": .7, "long-slot": .5}[hole]
        return 2.5*kb*d*thickness*fu*factor/1.25

    @staticmethod
    def bolt_tension(fub, fyb, area_net, area_shank):
        """17.3.5 / 17.4.5. Design resistance in N with Table 5 factors."""
        _positive(fub, fyb, area_net, area_shank)
        return min(.9*fub*area_net/1.25, fyb*area_shank/1.1)

    @staticmethod
    def bolt_interaction(v, vd, t, td):
        """17.3.6 or 17.4.6. Dimensionless utilisation, limit 1.0."""
        _positive(vd, td)
        return (v/vd)**2 + (t/td)**2

    @staticmethod
    def cl_10_3_6_bearing_bolt_combined_shear_and_tension(V_sb, V_db, T_b, T_db):
        """Draft 17.3.6. Retained project calculation and units."""
        return (V_sb / V_db) ** 2 + (T_b / T_db) ** 2

    @staticmethod
    def slip_resistance(fub, area_net, interfaces, mu, *, hole, load_level):
        """17.4.3. Return design force in N, Kh and gamma_mf."""
        _positive(fub, area_net, interfaces, mu)
        if int(interfaces) != interfaces or mu > .55:
            raise ValueError("Supply whole interface count and mu <= 0.55")
        kh = {"standard": 1, "oversize": .85, "short-slot": .85,
              "long-perpendicular": .85, "long-parallel": .70}[hole]
        gamma = {"service": 1.10, "ultimate": 1.25}[load_level]
        return mu*interfaces*kh*.70*fub*area_net/gamma, kh, gamma

    @staticmethod
    def cl_10_4_6_friction_bolt_combined_shear_and_tension(V_sf, V_df, T_f, T_df):
        """Draft 17.4.6. Retained project calculation and units."""
        return (V_sf / V_df) ** 2 + (T_f / T_df) ** 2

    @staticmethod
    def prying_force(te, lv, proof_stress, width_per_pair, t, fy, end, *, pretensioned):
        """17.4.7. Additional tensile force per bolt (N), for specified end plate."""
        _positive(lv, proof_stress, width_per_pair, t, fy, end)
        if te < 0 or not isinstance(pretensioned, bool):
            raise ValueError("Supply tensile force magnitude and boolean pretensioned")
        beta = 1 if pretensioned else 2
        le = min(end, 1.1*t*math.sqrt(beta*proof_stress/fy))
        return max(0, lv/(2*le)*(te-beta*1.5*proof_stress*width_per_pair*t**4/(27*le*lv**2)))

    @staticmethod
    def min_weld_size(t1, t2, *, first_run=False, preheated=False):
        """17.5.2.3, Table 21. Required size in mm for stated application."""
        _positive(t1, t2)
        thick, thin = max(t1,t2), min(t1,t2)
        if thick > 50 or thin < 3:
            raise NotImplementedError("Requires a separately qualified weld detail")
        size = 3 if thick <= 10 else 5 if thick <= 20 else 6 if thick <= 32 else (8 if first_run else 10)
        if size > thin and not preheated:
            raise ValueError("Thin-part exception requires preheating the thicker part")
        return min(size, thin)

    @staticmethod
    def weld_max_throat(t1, t2, *, special=False):
        """17.5.3.1. Upper throat limit in mm."""
        _positive(t1, t2)
        return min(t1,t2)*(1 if special else .7)

    @staticmethod
    def cl_10_5_3_1_max_weld_throat_thickness(part1_thickness, part2_thickness, special_circumstance=False):

        """Draft 17.5.3.1. Retained project calculation and units."""

        if special_circumstance is True:
            return min(part1_thickness, part2_thickness)
        else:
            return 0.7 * min(part1_thickness, part2_thickness)

    @staticmethod
    def weld_throat(size, angle):
        """17.5.3.1-2, Table 22. Check actual throat against 3 mm minimum."""
        _positive(size)
        for lo, hi, k in ((60,90,.70),(91,100,.65),(101,106,.60),(107,113,.55),(114,120,.50)):
            if lo <= angle <= hi:
                throat = k*size
                if throat < 3:
                    raise ValueError("Actual effective throat is below 3 mm")
                return throat
        raise ValueError("Fusion angle outside a printed Table 22 interval")

    @staticmethod
    def groove_throat(t1, t2, *, common_penetration=None):
        """17.5.3.3. For incomplete penetration give common weld metal excluding reinforcement."""
        _positive(t1, t2)
        thin = min(t1, t2)
        if common_penetration is None:
            return thin
        if not 0 < common_penetration <= thin:
            raise ValueError("Check common penetration")
        return common_penetration

    @staticmethod
    def fillet_effective_length(size, actual_length):
        """17.5.4.1, ordinary continuous fillet with end allowances, mm."""
        _positive(size, actual_length)
        if actual_length < 4*size:
            raise ValueError("Actual weld length below four weld sizes")
        return actual_length-2*size

    @staticmethod
    def weld_design_stress(fu_weld, fu_parent, *, fabrication):
        """17.5.7.1-2. Use weakest parent metal and weld ultimate strength (MPa)."""
        _positive(fu_weld, fu_parent)
        gamma = {"shop":1.25,"site":1.50}[fabrication]
        return min(fu_weld,fu_parent)/(math.sqrt(3)*gamma)

    @staticmethod
    def weld_long_joint(length, throat):
        """17.5.7.3. Splice/end connection loaded along its length, where applicable."""
        _positive(length, throat)
        beta = min(1, 1.2-.2*length/(150*throat))
        if beta <= 0:
            raise ValueError("Printed relation gives a nonpositive factor; review connection")
        return beta

    @staticmethod
    def steel_strength(grade, thickness):
        """Table 1 (viii, xvi). Return minimum fy, fu (MPa) for listed grades."""
        _positive(thickness)
        grades = {
            "E250": (250, 240, 230, 410), "E275": (275, 265, 255, 430),
            "E300": (300, 290, 280, 440), "E350": (350, 330, 320, 490),
            "E410": (410, 390, 380, 540), "E450": (450, 430, 420, 570),
            "E250S": (250, 240, 230, 410), "E300S": (300, 290, 280, 440),
            "E350S": (350, 330, 320, 490), "E450S": (450, 430, 420, 570),
        }
        row = grades[grade]
        index = 0 if thickness < 20 else 1 if thickness <= 40 else 2
        return row[index], row[3]

    @staticmethod
    def gradient_factor(row, ratio=None):
        """15.2.2 Table 14. Select diagram row 1-8, in printed order.
        Row 2 uses signed end-moment ratio psi. Rows 4,5,7,8 use M0/Mh.
        """
        fixed = {1: 1., 3: 1.05, 6: 1.10}
        if row in fixed:
            return fixed[row]
        if ratio is None or not math.isfinite(ratio):
            raise ValueError("Supply the ratio for this diagram")
        x = ratio
        if row == 2 and -1 <= x <= 1:
            return 1.25-.1*x-.15*x*x
        if x >= 0:
            if row == 4:
                return 1+1.35*x-.33*x**3 if x < 2 else 1.05
            if row == 5:
                return 1.25+.5*x**2-.275*x**4 if x < 1.47 else 1.05
            if row == 7:
                return 1+1.25*x-.30*x**3 if x < 2 else 1.10
            if row == 8:
                return 1.25+.325*x**2-.175*x**4 if x < 1.5 else 1.10
        raise ValueError("Unknown diagram or ratio outside its domain")

    @staticmethod
    def ltb_imperfection(section, *, h_over_b=None, tf=None, zez_over_zey=None):
        """Table 13. For unequal flanges h_over_b uses smaller flange width."""
        if section == "other-rolled":
            return .76
        if section in ("rolled-unequal", "welded-unequal"):
            _positive(h_over_b)
            if section == "rolled-unequal":
                return .21 if h_over_b <= 2 else .34
            return .49 if h_over_b <= 2 else .76
        _positive(tf, zez_over_zey)
        if section == "rolled":
            _positive(h_over_b)
            if h_over_b <= 1.2 or tf > 40:
                raise NotImplementedError("Repeated h/b condition in Table 13 requires clarification")
        elif section != "welded":
            raise ValueError("Unknown section")
        return min(.12*math.sqrt(zez_over_zey), .34)

    @staticmethod
    def specialty_fy(grade, thickness):
        """Table 1(xiv-xv). Minimum yield stress (MPa), at ambient temperature.
        Fire-resistant grade identifiers FR-Fe410, FR-Fe490; weathering grades below.
        At 25 mm, accept the entry only if the two printed ranges agree.
        """
        _positive(thickness)
        values = {"FR-Fe410": (300,280,260,240), "FR-Fe490": (350,330,310,290),
                  "WR-Fe480A": (345,325,325,None), "WR-Fe480B": (345,345,345,340),
                  "WR-Fe500": (355,None,None,None)}[grade]
        if thickness == 25 and values[1] != values[2]:
            raise NotImplementedError("Table 1 labels both adjacent ranges with 25")
        index = 0 if thickness < 12 else 1 if thickness <= 25 else 2 if thickness <= 40 else 3
        if values[index] is None:
            raise ValueError("Thickness/grade has no printed yield strength")
        return values[index]

    @staticmethod
    def thermal_movement(length, delta_temperature):
        """9.2.4.1(e), 10.5. Free movement in mm, positive for expansion.
        Restraint forces require a separate structural analysis.
        """
        _positive(length)
        if not math.isfinite(delta_temperature):
            raise ValueError("Temperature change must be finite")
        return 12e-6 * length * delta_temperature

    @staticmethod
    def fire_load_effect(dead, imposed, fire_restraint, *, storage):
        """10.3 and Table 4(v). Combine signed effects in the same units."""
        if type(storage) is not bool or not all(map(math.isfinite, (dead, imposed, fire_restraint))):
            raise ValueError("Supply finite load effects and a boolean storage flag")
        return dead + (imposed if storage else 0.5 * imposed) + fire_restraint

    @staticmethod
    def fire_yield_strength(fy20, temperature):
        """Mild or high-strength low-alloy steel only. MPa and degrees Celsius."""
        _positive(fy20)
        if not 20 <= temperature <= 905:
            raise ValueError("Supported steel temperature is 20 to 905 degrees Celsius")
        return fy20 * min(1.0, (905 - temperature) / 690)

    @staticmethod
    def frame_analysis_route(critical_factor, ultimate_factor, *, clad_without_infill_stiffness):
        """11.7.1. Classify the ratio for this frame; no structural solver is implied."""
        _positive(critical_factor, ultimate_factor)
        if type(clad_without_infill_stiffness) is not bool:
            raise ValueError("Specify whether this is the clause 11.7.1(a) frame case")
        lower, upper = (4.6, 10) if clad_without_infill_stiffness else (5.75, 20)
        ratio = critical_factor / ultimate_factor
        if ratio >= upper:
            return "first-order"
        if ratio >= lower:
            return "amplification-permitted"
        return "second-order"

    @staticmethod
    def elastic_amplification_allowed(ky, kz):
        """11.7.2.1(a). Check both moment factors for the elastic amplification route."""
        _positive(ky, kz)
        return max(ky, kz) <= 1.4

    @staticmethod
    def seismic_frame_route(zone, importance):
        """18.1.2-3. Earthquake-resisting frames only. Special detailing follows IS 18168."""
        if zone not in ('II', 'III', 'IV', 'V', 'VI') or importance not in (
                'normal', 'important', 'critical', 'special'):
            raise ValueError("Unknown seismic zone or importance category")
        if zone == 'II' and importance == 'important':
            raise NotImplementedError("18.1.2 and 18.1.3 overlap for important structures in zone II")
        if zone == 'II' and importance == 'normal':
            return "ordinary-permitted"
        return "special-required"

    @staticmethod
    def ocbf_brace_checks(section_class, slenderness, compression, resistance, gross_yield,
                          net_rupture, *, built_up, component_slenderness=None, central_bolts=None):
        """18.4.3.1. Return individual checks. Compression is a demand magnitude."""
        _positive(slenderness, resistance, gross_yield, net_rupture)
        if not math.isfinite(compression) or compression < 0 or type(built_up) is not bool:
            raise ValueError("Invalid compression demand or built-up flag")
        if section_class not in ('Plastic', 'Compact', 'Semi-Compact', 'Slender'):
            raise ValueError("Unknown cross-section class")
        checks = dict(section=section_class != 'Slender', slenderness=slenderness <= 120,
                      compression=compression <= 0.8 * resistance, yielding=gross_yield < net_rupture)
        if built_up:
            _positive(component_slenderness)
            if type(central_bolts) is not bool:
                raise ValueError("Identify bolts in the central quarter")
            checks.update(tack_spacing=component_slenderness <= 0.4 * slenderness,
                          central_quarter=not central_bolts)
        return checks

    @staticmethod
    def brace_connection_actions(fy, gross_area, combination_force, transferable_force, plastic_moment):
        """18.4.4.6. Return tensile force (N), moment (N mm) about buckling axis.
        Check rupture, block shear and gusset out-of-plane buckling separately.
        """
        _positive(fy, gross_area, plastic_moment)
        if any(not math.isfinite(x) or x < 0 for x in (combination_force, transferable_force)):
            raise ValueError("Supply nonnegative force magnitudes")
        return min(1.2 * fy * gross_area, combination_force, transferable_force), 1.2 * plastic_moment

    @staticmethod
    def anchor_steel(net_area, fy, fu, *, group, elongation_percent):
        """G-2.2.1 and G-2.3.1. Steel tension and pure shear (N) for the supplied area.
        For a group supply active steel area for the applicable load distribution.
        """
        _positive(net_area, fy, fu, elongation_percent)
        if fy > fu or type(group) is not bool:
            raise ValueError("Check material strengths and group status")
        ratio = fy / fu
        gamma_t = max(1.2 / ratio, 1.4)
        gamma_v = max(1 / ratio, 1.25) if fu <= 800 and ratio <= 0.8 else 1.5
        ductility_factor = 0.8 if group and elongation_percent < 8 else 1.0
        return net_area * fu / gamma_t, ductility_factor * 0.5 * net_area * fu / gamma_v

    @staticmethod
    def anchor_pullout(bearing_area, fck, *, cracked):
        """G-2.2.2. Head bearing pullout resistance in N, normal-weight M20 to M50 concrete."""
        _positive(bearing_area)
        if type(cracked) is not bool or not 20 <= fck <= 50:
            raise ValueError("Check concrete strength and cracking status")
        return 6.4 * (1 if cracked else 1.4) * bearing_area * fck

    @staticmethod
    def anchor_pyramid(fck, embedment, base_area, isolated_area, *, edge, spalling, eccentricity, cracking):
        """G-2.2.3. Supply actual projected areas and all four geometry/cracking factors."""
        _positive(embedment, base_area, isolated_area, edge, spalling, eccentricity, cracking)
        if not 20 <= fck <= 50:
            raise ValueError("Annex G concrete strength outside M20 to M50")
        basic = 7.2 * math.sqrt(fck) * embedment ** 1.5 / 2.15
        return basic * base_area / isolated_area * edge * spalling * eccentricity * cracking

    @staticmethod
    def anchor_pryout(embedment, pyramid_resistance):
        """G-2.3.3. Concrete pryout resistance in N from G-2.2.3 pyramid resistance."""
        _positive(embedment, pyramid_resistance)
        return (1 if embedment < 60 else 2) * pyramid_resistance


IS800_2025_Project = IS800_2025_Draft

# Printed grid, Tables 8(a-e) and 9(a-e). Each pair contains chi and fcd (MPa).
_COLUMN_FY = (200,210,220,230,240,250,260,280,300,320,340,360,380,400,420,450,480,510,540)
_COLUMN_TABLES = {
    "a0": {
        10: (
            (1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0),
            (182.0, 191.0, 200.0, 209.0, 218.0, 227.0, 236.0, 255.0, 273.0, 291.0, 309.0, 327.0, 345.0, 364.0, 382.0, 409.0, 436.0, 464.0, 491.0),
        ),
        20: (
            (1.0, 0.999, 0.998, 0.998, 0.997, 0.997, 0.996, 0.995, 0.994, 0.992, 0.991, 0.99, 0.989, 0.988, 0.987, 0.986, 0.984, 0.983, 0.981),
            (182.0, 191.0, 200.0, 209.0, 218.0, 226.0, 235.0, 253.0, 271.0, 289.0, 306.0, 324.0, 342.0, 359.0, 377.0, 403.0, 429.0, 456.0, 482.0),
        ),
        30: (
            (0.986, 0.985, 0.983, 0.982, 0.981, 0.98, 0.979, 0.977, 0.975, 0.973, 0.971, 0.969, 0.967, 0.965, 0.964, 0.961, 0.958, 0.955, 0.952),
            (179.0, 188.0, 197.0, 205.0, 214.0, 223.0, 231.0, 249.0, 266.0, 283.0, 300.0, 317.0, 334.0, 351.0, 368.0, 393.0, 418.0, 443.0, 467.0),
        ),
        40: (
            (0.97, 0.968, 0.966, 0.965, 0.963, 0.961, 0.96, 0.956, 0.953, 0.949, 0.946, 0.943, 0.939, 0.936, 0.932, 0.927, 0.921, 0.915, 0.909),
            (176.0, 185.0, 193.0, 202.0, 210.0, 218.0, 227.0, 243.0, 260.0, 276.0, 292.0, 308.0, 324.0, 340.0, 356.0, 379.0, 402.0, 424.0, 446.0),
        ),
        50: (
            (0.951, 0.948, 0.945, 0.943, 0.94, 0.937, 0.934, 0.929, 0.923, 0.917, 0.911, 0.905, 0.899, 0.892, 0.885, 0.874, 0.863, 0.852, 0.84),
            (173.0, 181.0, 189.0, 197.0, 205.0, 213.0, 221.0, 236.0, 252.0, 267.0, 282.0, 296.0, 310.0, 324.0, 338.0, 358.0, 377.0, 395.0, 412.0),
        ),
        60: (
            (0.927, 0.922, 0.918, 0.914, 0.909, 0.905, 0.9, 0.891, 0.881, 0.87, 0.86, 0.848, 0.837, 0.824, 0.812, 0.792, 0.772, 0.752, 0.731),
            (168.0, 176.0, 184.0, 191.0, 198.0, 206.0, 213.0, 227.0, 240.0, 253.0, 266.0, 278.0, 289.0, 300.0, 310.0, 324.0, 337.0, 349.0, 359.0),
        ),
        70: (
            (0.895, 0.888, 0.881, 0.874, 0.867, 0.859, 0.852, 0.836, 0.819, 0.802, 0.784, 0.766, 0.747, 0.728, 0.71, 0.682, 0.655, 0.629, 0.605),
            (163.0, 170.0, 176.0, 183.0, 189.0, 195.0, 201.0, 213.0, 223.0, 233.0, 242.0, 251.0, 258.0, 265.0, 271.0, 279.0, 286.0, 292.0, 297.0),
        ),
        80: (
            (0.851, 0.841, 0.83, 0.819, 0.808, 0.796, 0.784, 0.76, 0.736, 0.712, 0.687, 0.664, 0.641, 0.619, 0.598, 0.568, 0.54, 0.515, 0.491),
            (155.0, 160.0, 166.0, 171.0, 176.0, 181.0, 185.0, 194.0, 201.0, 207.0, 212.0, 217.0, 221.0, 225.0, 228.0, 232.0, 236.0, 239.0, 241.0),
        ),
        90: (
            (0.792, 0.777, 0.762, 0.747, 0.731, 0.716, 0.701, 0.67, 0.641, 0.614, 0.587, 0.563, 0.539, 0.518, 0.498, 0.47, 0.445, 0.422, 0.401),
            (144.0, 148.0, 152.0, 156.0, 160.0, 163.0, 166.0, 171.0, 175.0, 178.0, 182.0, 184.0, 186.0, 188.0, 190.0, 192.0, 194.0, 196.0, 197.0),
        ),
        100: (
            (0.721, 0.702, 0.683, 0.665, 0.647, 0.629, 0.612, 0.58, 0.55, 0.523, 0.498, 0.475, 0.453, 0.434, 0.416, 0.391, 0.369, 0.349, 0.332),
            (131.0, 134.0, 137.0, 139.0, 141.0, 143.0, 145.0, 148.0, 150.0, 152.0, 154.0, 155.0, 157.0, 158.0, 159.0, 160.0, 161.0, 162.0, 163.0),
        ),
        110: (
            (0.643, 0.622, 0.602, 0.583, 0.564, 0.547, 0.53, 0.499, 0.471, 0.446, 0.423, 0.403, 0.384, 0.366, 0.35, 0.329, 0.31, 0.293, 0.278),
            (117.0, 119.0, 120.0, 122.0, 123.0, 124.0, 125.0, 127.0, 129.0, 130.0, 131.0, 132.0, 133.0, 133.0, 134.0, 135.0, 135.0, 136.0, 136.0),
        ),
        120: (
            (0.568, 0.547, 0.527, 0.509, 0.491, 0.475, 0.459, 0.431, 0.405, 0.383, 0.363, 0.344, 0.328, 0.312, 0.299, 0.28, 0.264, 0.249, 0.236),
            (103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0, 110.0, 111.0, 111.0, 112.0, 113.0, 113.0, 114.0, 114.0, 115.0, 115.0, 115.0, 116.0),
        ),
        130: (
            (0.5, 0.48, 0.462, 0.445, 0.429, 0.414, 0.399, 0.374, 0.351, 0.331, 0.313, 0.297, 0.282, 0.269, 0.257, 0.241, 0.227, 0.214, 0.203),
            (91.0, 91.7, 92.4, 93.0, 93.5, 94.0, 94.4, 95.2, 95.8, 96.3, 96.8, 97.2, 97.6, 97.9, 98.2, 98.6, 98.9, 99.2, 99.4),
        ),
        140: (
            (0.441, 0.423, 0.406, 0.39, 0.376, 0.362, 0.35, 0.327, 0.307, 0.289, 0.273, 0.259, 0.246, 0.234, 0.223, 0.209, 0.197, 0.186, 0.176),
            (80.3, 80.8, 81.2, 81.6, 82.0, 82.3, 82.6, 83.2, 83.6, 84.0, 84.3, 84.6, 84.9, 85.1, 85.3, 85.6, 85.9, 86.1, 86.3),
        ),
        150: (
            (0.391, 0.374, 0.359, 0.345, 0.332, 0.319, 0.308, 0.288, 0.27, 0.254, 0.24, 0.227, 0.216, 0.205, 0.196, 0.183, 0.172, 0.163, 0.154),
            (71.1, 71.5, 71.8, 72.1, 72.3, 72.6, 72.8, 73.2, 73.5, 73.8, 74.0, 74.3, 74.5, 74.6, 74.8, 75.0, 75.2, 75.4, 75.5),
        ),
        160: (
            (0.348, 0.333, 0.319, 0.306, 0.294, 0.283, 0.273, 0.255, 0.239, 0.225, 0.212, 0.201, 0.191, 0.181, 0.173, 0.162, 0.152, 0.144, 0.136),
            (63.3, 63.6, 63.8, 64.0, 64.2, 64.4, 64.6, 64.8, 65.1, 65.3, 65.5, 65.7, 65.8, 66.0, 66.1, 66.3, 66.4, 66.5, 66.7),
        ),
        170: (
            (0.311, 0.298, 0.285, 0.273, 0.263, 0.253, 0.244, 0.227, 0.213, 0.2, 0.189, 0.179, 0.17, 0.161, 0.154, 0.144, 0.135, 0.128, 0.121),
            (56.6, 56.8, 57.0, 57.2, 57.3, 57.5, 57.6, 57.8, 58.0, 58.2, 58.3, 58.5, 58.6, 58.7, 58.8, 58.9, 59.1, 59.2, 59.3),
        ),
        180: (
            (0.28, 0.268, 0.256, 0.246, 0.236, 0.227, 0.219, 0.204, 0.191, 0.179, 0.169, 0.16, 0.152, 0.145, 0.138, 0.129, 0.121, 0.114, 0.108),
            (50.9, 51.1, 51.2, 51.3, 51.5, 51.6, 51.7, 51.9, 52.0, 52.1, 52.3, 52.4, 52.5, 52.6, 52.6, 52.7, 52.8, 52.9, 53.0),
        ),
        190: (
            (0.253, 0.242, 0.231, 0.222, 0.213, 0.205, 0.197, 0.184, 0.172, 0.162, 0.152, 0.144, 0.137, 0.13, 0.124, 0.116, 0.109, 0.103, 0.097),
            (46.0, 46.1, 46.2, 46.3, 46.4, 46.5, 46.6, 46.8, 46.9, 47.0, 47.1, 47.2, 47.3, 47.3, 47.4, 47.5, 47.6, 47.6, 47.7),
        ),
        200: (
            (0.23, 0.219, 0.21, 0.201, 0.193, 0.186, 0.179, 0.166, 0.156, 0.146, 0.138, 0.131, 0.124, 0.118, 0.112, 0.105, 0.099, 0.093, 0.088),
            (41.7, 41.9, 41.9, 42.0, 42.1, 42.2, 42.2, 42.4, 42.5, 42.6, 42.6, 42.7, 42.8, 42.8, 42.9, 43.0, 43.0, 43.1, 43.2),
        ),
        210: (
            (0.209, 0.2, 0.191, 0.183, 0.176, 0.169, 0.163, 0.151, 0.142, 0.133, 0.125, 0.119, 0.113, 0.107, 0.102, 0.095, 0.09, 0.084, 0.08),
            (38.0, 38.1, 38.2, 38.3, 38.3, 38.4, 38.5, 38.6, 38.6, 38.7, 38.8, 38.8, 38.9, 39.0, 39.0, 39.1, 39.1, 39.2, 39.2),
        ),
        220: (
            (0.191, 0.183, 0.175, 0.167, 0.161, 0.154, 0.149, 0.138, 0.129, 0.122, 0.115, 0.108, 0.103, 0.098, 0.093, 0.087, 0.082, 0.077, 0.073),
            (34.8, 34.9, 34.9, 35.0, 35.1, 35.1, 35.2, 35.2, 35.3, 35.4, 35.4, 35.5, 35.5, 35.6, 35.6, 35.7, 35.7, 35.8, 35.8),
        ),
        230: (
            (0.176, 0.168, 0.16, 0.154, 0.147, 0.142, 0.136, 0.127, 0.119, 0.112, 0.105, 0.099, 0.094, 0.09, 0.086, 0.08, 0.075, 0.071, 0.067),
            (32.0, 32.0, 32.1, 32.1, 32.2, 32.2, 32.3, 32.3, 32.4, 32.4, 32.5, 32.5, 32.6, 32.6, 32.7, 32.7, 32.7, 32.8, 32.8),
        ),
        240: (
            (0.162, 0.155, 0.148, 0.141, 0.136, 0.131, 0.126, 0.117, 0.109, 0.103, 0.097, 0.091, 0.087, 0.083, 0.079, 0.074, 0.069, 0.065, 0.061),
            (29.4, 29.5, 29.5, 29.6, 29.6, 29.7, 29.7, 29.8, 29.8, 29.9, 29.9, 29.9, 30.0, 30.0, 30.0, 30.1, 30.1, 30.2, 30.2),
        ),
        250: (
            (0.15, 0.143, 0.136, 0.131, 0.125, 0.121, 0.116, 0.108, 0.101, 0.095, 0.089, 0.084, 0.08, 0.076, 0.073, 0.068, 0.064, 0.06, 0.057),
            (27.2, 27.3, 27.3, 27.3, 27.4, 27.4, 27.4, 27.5, 27.5, 27.6, 27.6, 27.6, 27.7, 27.7, 27.7, 27.8, 27.8, 27.8, 27.9),
        ),
    },
    "a": {
        10: (
            (1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0),
            (182.0, 191.0, 200.0, 213.0, 218.0, 227.0, 236.0, 255.0, 273.0, 291.0, 309.0, 327.0, 345.0, 364.0, 382.0, 409.0, 436.0, 464.0, 491.0),
        ),
        20: (
            (1.0, 0.999, 0.998, 0.997, 0.995, 0.994, 0.993, 0.993, 0.99, 0.988, 0.986, 0.984, 0.983, 0.981, 0.979, 0.977, 0.975, 0.972, 0.97),
            (182.0, 191.0, 200.0, 208.0, 217.0, 226.0, 235.0, 252.0, 270.0, 287.0, 305.0, 322.0, 339.0, 357.0, 374.0, 400.0, 425.0, 451.0, 476.0),
        ),
        30: (
            (0.977, 0.975, 0.974, 0.972, 0.97, 0.969, 0.967, 0.965, 0.961, 0.957, 0.954, 0.951, 0.948, 0.946, 0.943, 0.938, 0.934, 0.93, 0.925),
            (178.0, 186.0, 195.0, 203.0, 212.0, 220.0, 229.0, 245.0, 262.0, 279.0, 295.0, 311.0, 328.0, 344.0, 360.0, 384.0, 408.0, 431.0, 454.0),
        ),
        40: (
            (0.952, 0.949, 0.947, 0.944, 0.942, 0.939, 0.937, 0.934, 0.926, 0.921, 0.916, 0.911, 0.906, 0.901, 0.896, 0.888, 0.881, 0.873, 0.865),
            (173.0, 181.0, 189.0, 197.0, 205.0, 213.0, 221.0, 237.0, 253.0, 268.0, 283.0, 298.0, 313.0, 328.0, 342.0, 363.0, 384.0, 405.0, 425.0),
        ),
        50: (
            (0.923, 0.919, 0.915, 0.911, 0.908, 0.904, 0.9, 0.896, 0.884, 0.876, 0.867, 0.859, 0.851, 0.842, 0.834, 0.82, 0.807, 0.794, 0.78),
            (168.0, 176.0, 183.0, 191.0, 198.0, 205.0, 213.0, 227.0, 241.0, 255.0, 268.0, 281.0, 294.0, 306.0, 318.0, 336.0, 352.0, 368.0, 383.0),
        ),
        60: (
            (0.888, 0.883, 0.877, 0.871, 0.865, 0.859, 0.853, 0.847, 0.828, 0.816, 0.803, 0.79, 0.777, 0.763, 0.75, 0.73, 0.71, 0.69, 0.671),
            (162.0, 169.0, 175.0, 182.0, 189.0, 195.0, 202.0, 214.0, 226.0, 237.0, 248.0, 258.0, 268.0, 278.0, 286.0, 299.0, 310.0, 320.0, 329.0),
        ),
        70: (
            (0.846, 0.837, 0.829, 0.82, 0.811, 0.803, 0.794, 0.785, 0.758, 0.74, 0.722, 0.703, 0.686, 0.668, 0.651, 0.626, 0.602, 0.579, 0.557),
            (154.0, 160.0, 166.0, 171.0, 177.0, 182.0, 188.0, 197.0, 207.0, 215.0, 223.0, 230.0, 237.0, 243.0, 249.0, 256.0, 263.0, 268.0, 274.0),
        ),
        80: (
            (0.793, 0.781, 0.769, 0.757, 0.746, 0.734, 0.722, 0.71, 0.675, 0.653, 0.631, 0.61, 0.589, 0.57, 0.551, 0.525, 0.501, 0.478, 0.458),
            (144.0, 149.0, 154.0, 158.0, 163.0, 167.0, 171.0, 178.0, 184.0, 190.0, 195.0, 199.0, 204.0, 207.0, 210.0, 215.0, 219.0, 222.0, 225.0),
        ),
        90: (
            (0.73, 0.715, 0.7, 0.685, 0.671, 0.657, 0.643, 0.628, 0.59, 0.565, 0.542, 0.52, 0.5, 0.481, 0.463, 0.439, 0.416, 0.396, 0.377),
            (133.0, 137.0, 140.0, 143.0, 146.0, 149.0, 152.0, 157.0, 161.0, 164.0, 168.0, 170.0, 173.0, 175.0, 177.0, 179.0, 182.0, 184.0, 185.0),
        ),
        100: (
            (0.661, 0.644, 0.627, 0.61, 0.594, 0.579, 0.564, 0.549, 0.51, 0.486, 0.463, 0.443, 0.424, 0.407, 0.39, 0.368, 0.348, 0.331, 0.314),
            (120.0, 123.0, 125.0, 128.0, 130.0, 132.0, 133.0, 136.0, 139.0, 141.0, 143.0, 145.0, 146.0, 148.0, 149.0, 151.0, 152.0, 153.0, 154.0),
        ),
        110: (
            (0.591, 0.573, 0.555, 0.538, 0.522, 0.507, 0.492, 0.478, 0.44, 0.418, 0.397, 0.379, 0.362, 0.346, 0.332, 0.312, 0.295, 0.279, 0.265),
            (107.0, 109.0, 111.0, 112.0, 114.0, 115.0, 116.0, 118.0, 120.0, 121.0, 123.0, 124.0, 125.0, 126.0, 127.0, 128.0, 129.0, 129.0, 130.0),
        ),
        120: (
            (0.525, 0.507, 0.489, 0.473, 0.458, 0.443, 0.429, 0.416, 0.381, 0.361, 0.343, 0.326, 0.311, 0.297, 0.284, 0.267, 0.252, 0.238, 0.226),
            (95.5, 96.7, 97.9, 98.9, 100.0, 101.0, 101.0, 103.0, 104.0, 105.0, 106.0, 107.0, 107.0, 108.0, 109.0, 109.0, 110.0, 110.0, 111.0),
        ),
        130: (
            (0.466, 0.448, 0.432, 0.416, 0.402, 0.388, 0.376, 0.364, 0.332, 0.314, 0.298, 0.283, 0.269, 0.257, 0.246, 0.231, 0.217, 0.206, 0.195),
            (84.6, 85.5, 86.3, 87.0, 87.7, 88.3, 88.8, 89.8, 90.6, 91.3, 92.0, 92.5, 93.0, 93.5, 93.9, 94.4, 94.9, 95.3, 95.7),
        ),
        140: (
            (0.413, 0.397, 0.382, 0.368, 0.355, 0.342, 0.331, 0.32, 0.291, 0.275, 0.26, 0.247, 0.235, 0.224, 0.214, 0.201, 0.189, 0.179, 0.17),
            (75.2, 75.8, 76.4, 76.9, 77.4, 77.8, 78.2, 78.9, 79.5, 80.0, 80.5, 80.9, 81.3, 81.6, 81.9, 82.3, 82.6, 83.0, 83.2),
        ),
        150: (
            (0.368, 0.353, 0.339, 0.326, 0.314, 0.303, 0.293, 0.283, 0.257, 0.243, 0.229, 0.218, 0.207, 0.197, 0.189, 0.177, 0.166, 0.157, 0.149),
            (67.0, 67.4, 67.9, 68.2, 68.6, 68.9, 69.2, 69.7, 70.2, 70.6, 70.9, 71.2, 71.5, 71.8, 72.0, 72.3, 72.6, 72.9, 73.1),
        ),
        160: (
            (0.329, 0.316, 0.303, 0.291, 0.28, 0.27, 0.261, 0.252, 0.229, 0.215, 0.204, 0.193, 0.184, 0.175, 0.167, 0.157, 0.147, 0.139, 0.132),
            (59.9, 60.3, 60.6, 60.9, 61.1, 61.4, 61.6, 62.0, 62.4, 62.7, 62.9, 63.2, 63.4, 63.6, 63.8, 64.0, 64.3, 64.5, 64.6),
        ),
        170: (
            (0.296, 0.283, 0.272, 0.261, 0.251, 0.242, 0.233, 0.225, 0.204, 0.192, 0.182, 0.172, 0.164, 0.156, 0.149, 0.14, 0.131, 0.124, 0.117),
            (53.8, 54.1, 54.3, 54.6, 54.8, 55.0, 55.1, 55.5, 55.7, 56.0, 56.2, 56.4, 56.6, 56.7, 56.9, 57.1, 57.3, 57.4, 57.6),
        ),
        180: (
            (0.267, 0.255, 0.245, 0.235, 0.226, 0.218, 0.21, 0.203, 0.184, 0.173, 0.163, 0.155, 0.147, 0.14, 0.134, 0.125, 0.118, 0.111, 0.105),
            (48.6, 48.8, 49.0, 49.2, 49.3, 49.5, 49.6, 49.9, 50.1, 50.3, 50.5, 50.6, 50.8, 50.9, 51.0, 51.2, 51.3, 51.5, 51.6),
        ),
        190: (
            (0.242, 0.231, 0.222, 0.213, 0.205, 0.197, 0.19, 0.183, 0.166, 0.156, 0.147, 0.14, 0.133, 0.126, 0.121, 0.113, 0.106, 0.1, 0.095),
            (44.0, 44.2, 44.3, 44.5, 44.6, 44.7, 44.9, 45.1, 45.3, 45.4, 45.6, 45.7, 45.8, 45.9, 46.0, 46.2, 46.3, 46.4, 46.5),
        ),
        200: (
            (0.22, 0.21, 0.202, 0.193, 0.186, 0.179, 0.172, 0.166, 0.151, 0.142, 0.134, 0.127, 0.12, 0.115, 0.109, 0.102, 0.096, 0.091, 0.086),
            (40.0, 40.2, 40.3, 40.4, 40.5, 40.7, 40.7, 40.9, 41.1, 41.2, 41.3, 41.4, 41.5, 41.6, 41.7, 41.8, 41.9, 42.0, 42.1),
        ),
        210: (
            (0.201, 0.192, 0.184, 0.177, 0.17, 0.163, 0.157, 0.152, 0.137, 0.129, 0.122, 0.115, 0.11, 0.104, 0.099, 0.093, 0.087, 0.083, 0.078),
            (36.6, 36.7, 36.8, 36.9, 37.0, 37.1, 37.2, 37.3, 37.4, 37.6, 37.7, 37.8, 37.8, 37.9, 38.0, 38.1, 38.2, 38.3, 38.3),
        ),
        220: (
            (0.184, 0.176, 0.169, 0.162, 0.155, 0.149, 0.144, 0.139, 0.126, 0.118, 0.111, 0.106, 0.1, 0.095, 0.091, 0.085, 0.08, 0.075, 0.071),
            (33.5, 33.6, 33.7, 33.8, 33.9, 34.0, 34.0, 34.2, 34.3, 34.4, 34.5, 34.5, 34.6, 34.7, 34.7, 34.8, 34.9, 35.0, 35.0),
        ),
        230: (
            (0.17, 0.162, 0.155, 0.149, 0.143, 0.137, 0.132, 0.128, 0.115, 0.108, 0.102, 0.097, 0.092, 0.088, 0.083, 0.078, 0.073, 0.069, 0.065),
            (30.8, 30.9, 31.0, 31.1, 31.2, 31.2, 31.3, 31.4, 31.5, 31.6, 31.6, 31.7, 31.8, 31.8, 31.9, 31.9, 32.0, 32.1, 32.1),
        ),
        240: (
            (0.157, 0.149, 0.143, 0.137, 0.132, 0.127, 0.122, 0.118, 0.106, 0.1, 0.094, 0.089, 0.085, 0.081, 0.077, 0.072, 0.068, 0.064, 0.06),
            (28.5, 28.5, 28.6, 28.7, 28.7, 28.8, 28.8, 28.9, 29.0, 29.1, 29.1, 29.2, 29.3, 29.3, 29.4, 29.4, 29.5, 29.5, 29.6),
        ),
        250: (
            (0.145, 0.138, 0.132, 0.127, 0.122, 0.117, 0.113, 0.109, 0.098, 0.092, 0.087, 0.082, 0.078, 0.074, 0.071, 0.066, 0.062, 0.059, 0.056),
            (26.3, 26.4, 26.5, 26.5, 26.6, 26.6, 26.7, 26.7, 26.8, 26.9, 26.9, 27.0, 27.0, 27.1, 27.1, 27.2, 27.2, 27.3, 27.3),
        ),
    },
    "b": {
        10: (
            (1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0),
            (182.0, 191.0, 200.0, 209.0, 218.0, 227.0, 236.0, 255.0, 273.0, 291.0, 309.0, 327.0, 345.0, 364.0, 382.0, 409.0, 436.0, 464.0, 491.0),
        ),
        20: (
            (1.0, 0.998, 0.996, 0.994, 0.993, 0.991, 0.99, 0.986, 0.983, 0.981, 0.978, 0.975, 0.972, 0.97, 0.967, 0.963, 0.96, 0.956, 0.953),
            (182.0, 190.0, 199.0, 208.0, 217.0, 225.0, 234.0, 251.0, 268.0, 285.0, 302.0, 319.0, 336.0, 353.0, 369.0, 394.0, 419.0, 443.0, 468.0),
        ),
        30: (
            (0.963, 0.961, 0.958, 0.955, 0.953, 0.95, 0.948, 0.943, 0.938, 0.933, 0.929, 0.924, 0.92, 0.915, 0.911, 0.904, 0.898, 0.892, 0.886),
            (175.0, 183.0, 192.0, 200.0, 208.0, 216.0, 224.0, 240.0, 256.0, 271.0, 287.0, 302.0, 318.0, 333.0, 348.0, 370.0, 392.0, 414.0, 435.0),
        ),
        40: (
            (0.925, 0.921, 0.917, 0.913, 0.909, 0.906, 0.902, 0.895, 0.887, 0.88, 0.873, 0.866, 0.859, 0.852, 0.845, 0.835, 0.825, 0.815, 0.805),
            (168.0, 176.0, 183.0, 191.0, 198.0, 206.0, 213.0, 228.0, 242.0, 256.0, 270.0, 283.0, 297.0, 310.0, 323.0, 342.0, 360.0, 378.0, 395.0),
        ),
        50: (
            (0.883, 0.877, 0.872, 0.866, 0.861, 0.855, 0.85, 0.839, 0.829, 0.818, 0.808, 0.798, 0.787, 0.777, 0.767, 0.752, 0.737, 0.722, 0.708),
            (161.0, 167.0, 174.0, 181.0, 188.0, 194.0, 201.0, 214.0, 226.0, 238.0, 250.0, 261.0, 272.0, 283.0, 293.0, 308.0, 322.0, 335.0, 347.0),
        ),
        60: (
            (0.835, 0.827, 0.82, 0.812, 0.805, 0.798, 0.79, 0.775, 0.761, 0.746, 0.732, 0.718, 0.704, 0.691, 0.677, 0.657, 0.638, 0.62, 0.602),
            (152.0, 158.0, 164.0, 170.0, 176.0, 181.0, 187.0, 197.0, 207.0, 217.0, 226.0, 235.0, 243.0, 251.0, 259.0, 269.0, 279.0, 287.0, 295.0),
        ),
        70: (
            (0.781, 0.771, 0.761, 0.751, 0.742, 0.732, 0.722, 0.703, 0.685, 0.667, 0.649, 0.632, 0.615, 0.599, 0.584, 0.561, 0.54, 0.52, 0.502),
            (142.0, 147.0, 152.0, 157.0, 162.0, 166.0, 171.0, 179.0, 187.0, 194.0, 201.0, 207.0, 213.0, 218.0, 223.0, 230.0, 236.0, 241.0, 246.0),
        ),
        80: (
            (0.721, 0.709, 0.697, 0.685, 0.673, 0.661, 0.65, 0.627, 0.606, 0.585, 0.566, 0.547, 0.529, 0.512, 0.496, 0.474, 0.453, 0.434, 0.416),
            (131.0, 135.0, 139.0, 143.0, 147.0, 150.0, 154.0, 160.0, 165.0, 170.0, 175.0, 179.0, 183.0, 186.0, 190.0, 194.0, 198.0, 201.0, 204.0),
        ),
        90: (
            (0.657, 0.643, 0.629, 0.615, 0.602, 0.589, 0.576, 0.552, 0.53, 0.508, 0.488, 0.47, 0.452, 0.436, 0.421, 0.4, 0.38, 0.363, 0.346),
            (120.0, 123.0, 126.0, 129.0, 131.0, 134.0, 136.0, 141.0, 144.0, 148.0, 151.0, 154.0, 156.0, 159.0, 161.0, 163.0, 166.0, 168.0, 170.0),
        ),
        100: (
            (0.593, 0.577, 0.562, 0.548, 0.534, 0.52, 0.507, 0.483, 0.461, 0.44, 0.421, 0.403, 0.387, 0.372, 0.358, 0.339, 0.321, 0.306, 0.291),
            (108.0, 110.0, 112.0, 114.0, 116.0, 118.0, 120.0, 123.0, 126.0, 128.0, 130.0, 132.0, 134.0, 135.0, 137.0, 139.0, 140.0, 142.0, 143.0),
        ),
        110: (
            (0.531, 0.515, 0.5, 0.485, 0.471, 0.458, 0.445, 0.422, 0.401, 0.381, 0.364, 0.348, 0.333, 0.319, 0.306, 0.289, 0.274, 0.26, 0.247),
            (96.5, 98.3, 100.0, 101.0, 103.0, 104.0, 105.0, 107.0, 109.0, 111.0, 112.0, 114.0, 115.0, 116.0, 117.0, 118.0, 119.0, 121.0, 121.0),
        ),
        120: (
            (0.474, 0.458, 0.443, 0.429, 0.416, 0.403, 0.391, 0.37, 0.35, 0.332, 0.316, 0.301, 0.288, 0.276, 0.265, 0.249, 0.236, 0.223, 0.212),
            (86.2, 87.5, 88.6, 89.7, 90.7, 91.7, 92.5, 94.1, 95.4, 96.6, 97.7, 98.6, 100.0, 100.0, 101.0, 102.0, 103.0, 104.0, 104.0),
        ),
        130: (
            (0.423, 0.408, 0.394, 0.38, 0.368, 0.356, 0.345, 0.325, 0.307, 0.291, 0.276, 0.263, 0.251, 0.24, 0.23, 0.217, 0.204, 0.194, 0.184),
            (76.9, 77.8, 78.7, 79.5, 80.3, 81.0, 81.6, 82.7, 83.7, 84.6, 85.4, 86.1, 86.8, 87.3, 87.9, 88.6, 89.2, 89.8, 90.3),
        ),
        140: (
            (0.378, 0.364, 0.35, 0.338, 0.327, 0.316, 0.306, 0.287, 0.271, 0.256, 0.243, 0.231, 0.221, 0.211, 0.202, 0.19, 0.179, 0.169, 0.161),
            (68.7, 69.4, 70.1, 70.7, 71.3, 71.8, 72.3, 73.1, 73.9, 74.6, 75.2, 75.7, 76.2, 76.6, 77.1, 77.6, 78.1, 78.5, 78.9),
        ),
        150: (
            (0.339, 0.325, 0.313, 0.302, 0.291, 0.281, 0.272, 0.255, 0.241, 0.227, 0.215, 0.205, 0.195, 0.186, 0.178, 0.167, 0.158, 0.149, 0.142),
            (61.6, 62.1, 62.6, 63.1, 63.6, 64.0, 64.3, 65.0, 65.6, 66.1, 66.6, 67.0, 67.4, 67.7, 68.1, 68.5, 68.9, 69.2, 69.5),
        ),
        160: (
            (0.305, 0.292, 0.281, 0.271, 0.261, 0.252, 0.243, 0.228, 0.215, 0.203, 0.192, 0.182, 0.174, 0.166, 0.158, 0.149, 0.14, 0.133, 0.126),
            (55.4, 55.8, 56.2, 56.6, 56.9, 57.3, 57.5, 58.1, 58.5, 59.0, 59.3, 59.7, 60.0, 60.3, 60.5, 60.9, 61.2, 61.5, 61.7),
        ),
        170: (
            (0.275, 0.264, 0.253, 0.244, 0.235, 0.227, 0.219, 0.205, 0.193, 0.182, 0.172, 0.163, 0.155, 0.148, 0.142, 0.133, 0.125, 0.118, 0.112),
            (50.0, 50.3, 50.7, 51.0, 51.2, 51.5, 51.7, 52.2, 52.5, 52.9, 53.2, 53.5, 53.7, 53.9, 54.1, 54.4, 54.7, 54.9, 55.1),
        ),
        180: (
            (0.249, 0.239, 0.229, 0.22, 0.212, 0.205, 0.198, 0.185, 0.174, 0.164, 0.155, 0.147, 0.14, 0.133, 0.128, 0.12, 0.113, 0.106, 0.101),
            (45.3, 45.6, 45.9, 46.1, 46.3, 46.5, 46.7, 47.1, 47.4, 47.7, 47.9, 48.1, 48.3, 48.5, 48.7, 48.9, 49.2, 49.3, 49.5),
        ),
        190: (
            (0.227, 0.217, 0.208, 0.2, 0.193, 0.186, 0.179, 0.168, 0.157, 0.148, 0.14, 0.133, 0.127, 0.121, 0.115, 0.108, 0.102, 0.096, 0.091),
            (41.2, 41.5, 41.7, 41.9, 42.1, 42.2, 42.4, 42.7, 42.9, 43.2, 43.4, 43.6, 43.7, 43.9, 44.0, 44.2, 44.4, 44.6, 44.7),
        ),
        200: (
            (0.207, 0.198, 0.19, 0.183, 0.176, 0.169, 0.163, 0.153, 0.143, 0.135, 0.128, 0.121, 0.115, 0.11, 0.105, 0.098, 0.092, 0.087, 0.083),
            (37.6, 37.8, 38.0, 38.2, 38.3, 38.5, 38.6, 38.9, 39.1, 39.3, 39.5, 39.6, 39.8, 39.9, 40.0, 40.2, 40.3, 40.5, 40.6),
        ),
        210: (
            (0.19, 0.182, 0.174, 0.167, 0.161, 0.155, 0.149, 0.14, 0.131, 0.123, 0.117, 0.11, 0.105, 0.1, 0.096, 0.09, 0.084, 0.08, 0.075),
            (34.5, 34.7, 34.8, 35.0, 35.1, 35.2, 35.3, 35.5, 35.7, 35.9, 36.0, 36.2, 36.3, 36.4, 36.5, 36.6, 36.8, 36.9, 37.0),
        ),
        220: (
            (0.174, 0.167, 0.16, 0.154, 0.148, 0.142, 0.137, 0.128, 0.12, 0.113, 0.107, 0.101, 0.096, 0.092, 0.088, 0.082, 0.077, 0.073, 0.069),
            (31.7, 31.9, 32.0, 32.1, 32.2, 32.3, 32.4, 32.6, 32.8, 32.9, 33.0, 33.1, 33.2, 33.3, 33.4, 33.6, 33.7, 33.8, 33.9),
        ),
        230: (
            (0.161, 0.154, 0.147, 0.141, 0.136, 0.131, 0.126, 0.118, 0.111, 0.104, 0.098, 0.093, 0.088, 0.084, 0.08, 0.075, 0.071, 0.067, 0.063),
            (29.2, 29.4, 29.5, 29.6, 29.7, 29.8, 29.9, 30.0, 30.1, 30.3, 30.4, 30.5, 30.6, 30.7, 30.7, 30.8, 30.9, 31.0, 31.1),
        ),
        240: (
            (0.149, 0.142, 0.136, 0.131, 0.126, 0.121, 0.117, 0.109, 0.102, 0.096, 0.091, 0.086, 0.082, 0.078, 0.074, 0.07, 0.065, 0.062, 0.058),
            (27.1, 27.2, 27.3, 27.3, 27.4, 27.5, 27.6, 27.7, 27.8, 27.9, 28.0, 28.1, 28.2, 28.3, 28.3, 28.4, 28.5, 28.6, 28.7),
        ),
        250: (
            (0.138, 0.132, 0.126, 0.121, 0.117, 0.112, 0.108, 0.101, 0.095, 0.089, 0.084, 0.08, 0.076, 0.072, 0.069, 0.064, 0.06, 0.057, 0.054),
            (25.1, 25.2, 25.3, 25.3, 25.4, 25.5, 25.6, 25.7, 25.8, 25.9, 26.0, 26.0, 26.1, 26.2, 26.2, 26.3, 26.4, 26.5, 26.5),
        ),
    },
    "c": {
        10: (
            (1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0),
            (182.0, 191.0, 200.0, 209.0, 218.0, 227.0, 236.0, 255.0, 273.0, 291.0, 309.0, 327.0, 345.0, 364.0, 382.0, 409.0, 436.0, 464.0, 491.0),
        ),
        20: (
            (0.999, 0.997, 0.994, 0.992, 0.99, 0.987, 0.985, 0.981, 0.976, 0.972, 0.968, 0.964, 0.961, 0.957, 0.953, 0.948, 0.943, 0.938, 0.933),
            (182.0, 190.0, 199.0, 207.0, 216.0, 224.0, 233.0, 250.0, 266.0, 283.0, 299.0, 316.0, 332.0, 348.0, 364.0, 388.0, 412.0, 435.0, 458.0),
        ),
        30: (
            (0.948, 0.944, 0.941, 0.937, 0.933, 0.93, 0.926, 0.92, 0.913, 0.907, 0.901, 0.895, 0.889, 0.883, 0.877, 0.869, 0.861, 0.853, 0.845),
            (172.0, 180.0, 188.0, 196.0, 204.0, 211.0, 219.0, 234.0, 249.0, 264.0, 278.0, 293.0, 307.0, 321.0, 335.0, 355.0, 376.0, 395.0, 415.0),
        ),
        40: (
            (0.896, 0.891, 0.885, 0.88, 0.875, 0.87, 0.866, 0.856, 0.847, 0.838, 0.829, 0.82, 0.812, 0.803, 0.795, 0.783, 0.771, 0.76, 0.748),
            (163.0, 170.0, 177.0, 184.0, 191.0, 198.0, 205.0, 218.0, 231.0, 244.0, 256.0, 268.0, 280.0, 292.0, 304.0, 320.0, 337.0, 352.0, 367.0),
        ),
        50: (
            (0.841, 0.834, 0.827, 0.821, 0.814, 0.807, 0.801, 0.788, 0.776, 0.763, 0.752, 0.74, 0.729, 0.717, 0.706, 0.69, 0.675, 0.66, 0.645),
            (153.0, 159.0, 165.0, 172.0, 178.0, 183.0, 189.0, 201.0, 212.0, 222.0, 232.0, 242.0, 252.0, 261.0, 270.0, 282.0, 295.0, 306.0, 317.0),
        ),
        60: (
            (0.783, 0.774, 0.765, 0.757, 0.748, 0.74, 0.732, 0.716, 0.7, 0.685, 0.67, 0.656, 0.642, 0.628, 0.615, 0.596, 0.578, 0.561, 0.544),
            (142.0, 148.0, 153.0, 158.0, 163.0, 168.0, 173.0, 182.0, 191.0, 199.0, 207.0, 215.0, 222.0, 228.0, 235.0, 244.0, 252.0, 260.0, 267.0),
        ),
        70: (
            (0.722, 0.711, 0.7, 0.69, 0.68, 0.67, 0.66, 0.641, 0.623, 0.605, 0.588, 0.572, 0.557, 0.542, 0.528, 0.508, 0.489, 0.471, 0.454),
            (131.0, 136.0, 140.0, 144.0, 148.0, 152.0, 156.0, 163.0, 170.0, 176.0, 182.0, 187.0, 192.0, 197.0, 202.0, 208.0, 213.0, 218.0, 223.0),
        ),
        80: (
            (0.659, 0.646, 0.634, 0.622, 0.611, 0.6, 0.589, 0.568, 0.548, 0.529, 0.512, 0.495, 0.479, 0.464, 0.45, 0.43, 0.412, 0.395, 0.379),
            (120.0, 123.0, 127.0, 130.0, 133.0, 136.0, 139.0, 145.0, 149.0, 154.0, 158.0, 162.0, 165.0, 169.0, 172.0, 176.0, 180.0, 183.0, 186.0),
        ),
        90: (
            (0.596, 0.583, 0.569, 0.557, 0.544, 0.533, 0.521, 0.499, 0.479, 0.46, 0.443, 0.426, 0.411, 0.397, 0.383, 0.365, 0.348, 0.332, 0.318),
            (108.0, 111.0, 114.0, 116.0, 119.0, 121.0, 123.0, 127.0, 131.0, 134.0, 137.0, 140.0, 142.0, 144.0, 146.0, 149.0, 152.0, 154.0, 156.0),
        ),
        100: (
            (0.536, 0.522, 0.508, 0.495, 0.483, 0.471, 0.459, 0.438, 0.418, 0.4, 0.384, 0.368, 0.354, 0.341, 0.328, 0.311, 0.296, 0.282, 0.269),
            (97.5, 100.0, 102.0, 104.0, 105.0, 107.0, 109.0, 112.0, 114.0, 116.0, 119.0, 120.0, 122.0, 124.0, 125.0, 127.0, 129.0, 131.0, 132.0),
        ),
        110: (
            (0.48, 0.466, 0.453, 0.44, 0.428, 0.416, 0.405, 0.385, 0.366, 0.349, 0.333, 0.319, 0.306, 0.294, 0.283, 0.268, 0.254, 0.242, 0.23),
            (87.3, 89.0, 90.5, 92.0, 93.3, 94.6, 95.7, 97.9, 100.0, 102.0, 103.0, 104.0, 106.0, 107.0, 108.0, 110.0, 111.0, 112.0, 113.0),
        ),
        120: (
            (0.43, 0.416, 0.403, 0.391, 0.379, 0.368, 0.358, 0.339, 0.321, 0.306, 0.291, 0.278, 0.267, 0.256, 0.246, 0.232, 0.22, 0.209, 0.199),
            (78.2, 79.4, 80.6, 81.7, 82.7, 83.7, 84.6, 86.2, 87.6, 88.9, 90.1, 91.1, 92.1, 93.0, 93.8, 94.9, 95.9, 96.8, 97.6),
        ),
        130: (
            (0.385, 0.372, 0.36, 0.348, 0.337, 0.327, 0.317, 0.299, 0.283, 0.269, 0.256, 0.244, 0.234, 0.224, 0.215, 0.203, 0.192, 0.182, 0.173),
            (70.0, 71.0, 71.9, 72.8, 73.5, 74.3, 75.0, 76.2, 77.3, 78.3, 79.2, 80.0, 80.7, 81.4, 82.0, 82.9, 83.6, 84.3, 84.9),
        ),
        140: (
            (0.346, 0.333, 0.322, 0.311, 0.301, 0.291, 0.282, 0.266, 0.251, 0.238, 0.227, 0.216, 0.206, 0.197, 0.189, 0.178, 0.168, 0.16, 0.152),
            (62.9, 63.6, 64.4, 65.0, 65.6, 66.2, 66.7, 67.7, 68.6, 69.3, 70.0, 70.7, 71.2, 71.8, 72.3, 72.9, 73.5, 74.1, 74.6),
        ),
        150: (
            (0.311, 0.3, 0.289, 0.279, 0.269, 0.261, 0.252, 0.237, 0.224, 0.212, 0.202, 0.192, 0.183, 0.175, 0.168, 0.158, 0.149, 0.141, 0.134),
            (56.6, 57.2, 57.8, 58.3, 58.8, 59.2, 59.7, 60.4, 61.1, 61.7, 62.3, 62.8, 63.3, 63.7, 64.1, 64.6, 65.1, 65.5, 65.9),
        ),
        160: (
            (0.281, 0.27, 0.26, 0.251, 0.242, 0.234, 0.227, 0.213, 0.201, 0.19, 0.18, 0.172, 0.164, 0.156, 0.15, 0.141, 0.133, 0.126, 0.12),
            (51.1, 51.6, 52.1, 52.5, 52.9, 53.3, 53.6, 54.2, 54.8, 55.3, 55.7, 56.1, 56.5, 56.9, 57.2, 57.6, 58.0, 58.4, 58.7),
        ),
        170: (
            (0.255, 0.245, 0.236, 0.227, 0.219, 0.212, 0.205, 0.192, 0.181, 0.171, 0.162, 0.154, 0.147, 0.14, 0.134, 0.126, 0.119, 0.113, 0.107),
            (46.4, 46.8, 47.1, 47.5, 47.8, 48.1, 48.4, 48.9, 49.3, 49.8, 50.1, 50.5, 50.8, 51.1, 51.3, 51.7, 52.0, 52.3, 52.6),
        ),
        180: (
            (0.232, 0.223, 0.214, 0.206, 0.199, 0.192, 0.186, 0.174, 0.164, 0.155, 0.147, 0.139, 0.133, 0.127, 0.121, 0.114, 0.107, 0.102, 0.096),
            (42.2, 42.5, 42.8, 43.1, 43.4, 43.6, 43.9, 44.3, 44.7, 45.0, 45.3, 45.6, 45.8, 46.1, 46.3, 46.6, 46.9, 47.1, 47.3),
        ),
        190: (
            (0.212, 0.203, 0.195, 0.188, 0.181, 0.175, 0.169, 0.158, 0.149, 0.14, 0.133, 0.126, 0.12, 0.115, 0.11, 0.103, 0.097, 0.092, 0.087),
            (38.5, 38.8, 39.0, 39.3, 39.5, 39.7, 39.9, 40.3, 40.6, 40.9, 41.1, 41.4, 41.6, 41.8, 42.0, 42.2, 42.5, 42.7, 42.9),
        ),
        200: (
            (0.194, 0.186, 0.179, 0.172, 0.166, 0.16, 0.154, 0.144, 0.136, 0.128, 0.121, 0.115, 0.11, 0.105, 0.1, 0.094, 0.089, 0.084, 0.079),
            (35.3, 35.5, 35.7, 35.9, 36.1, 36.3, 36.5, 36.8, 37.0, 37.3, 37.5, 37.7, 37.9, 38.1, 38.2, 38.4, 38.6, 38.8, 39.0),
        ),
        210: (
            (0.178, 0.171, 0.164, 0.158, 0.152, 0.146, 0.141, 0.132, 0.124, 0.117, 0.111, 0.105, 0.1, 0.096, 0.092, 0.086, 0.081, 0.076, 0.072),
            (32.4, 32.6, 32.8, 33.0, 33.1, 33.3, 33.4, 33.7, 33.9, 34.1, 34.3, 34.5, 34.7, 34.8, 34.9, 35.1, 35.3, 35.4, 35.6),
        ),
        220: (
            (0.164, 0.157, 0.151, 0.145, 0.14, 0.135, 0.13, 0.122, 0.114, 0.108, 0.102, 0.097, 0.092, 0.088, 0.084, 0.079, 0.074, 0.07, 0.066),
            (29.9, 30.1, 30.2, 30.4, 30.5, 30.6, 30.8, 31.0, 31.2, 31.4, 31.5, 31.7, 31.8, 31.9, 32.1, 32.2, 32.4, 32.5, 32.6),
        ),
        230: (
            (0.152, 0.145, 0.14, 0.134, 0.129, 0.124, 0.12, 0.112, 0.105, 0.099, 0.094, 0.089, 0.085, 0.081, 0.077, 0.073, 0.068, 0.065, 0.061),
            (27.6, 27.8, 27.9, 28.0, 28.2, 28.3, 28.4, 28.6, 28.8, 28.9, 29.1, 29.2, 29.3, 29.4, 29.5, 29.7, 29.8, 29.9, 30.0),
        ),
        240: (
            (0.141, 0.135, 0.129, 0.124, 0.12, 0.115, 0.111, 0.104, 0.098, 0.092, 0.087, 0.082, 0.078, 0.075, 0.071, 0.067, 0.063, 0.06, 0.056),
            (25.6, 25.7, 25.9, 26.0, 26.1, 26.2, 26.3, 26.4, 26.6, 26.7, 26.9, 27.0, 27.1, 27.2, 27.3, 27.4, 27.5, 27.6, 27.7),
        ),
        250: (
            (0.131, 0.125, 0.12, 0.115, 0.111, 0.107, 0.103, 0.096, 0.09, 0.085, 0.081, 0.076, 0.073, 0.069, 0.066, 0.062, 0.058, 0.055, 0.052),
            (23.8, 23.9, 24.0, 24.1, 24.2, 24.3, 24.4, 24.5, 24.7, 24.8, 24.9, 25.0, 25.1, 25.2, 25.3, 25.4, 25.5, 25.6, 25.7),
        ),
    },
    "d": {
        10: (
            (1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0),
            (182.0, 191.0, 200.0, 209.0, 218.0, 227.0, 236.0, 255.0, 273.0, 291.0, 309.0, 327.0, 345.0, 364.0, 382.0, 409.0, 436.0, 464.0, 491.0),
        ),
        20: (
            (0.999, 0.995, 0.991, 0.988, 0.984, 0.98, 0.977, 0.97, 0.964, 0.958, 0.952, 0.946, 0.94, 0.935, 0.93, 0.922, 0.915, 0.908, 0.901),
            (182.0, 190.0, 198.0, 206.0, 215.0, 223.0, 231.0, 247.0, 263.0, 279.0, 294.0, 310.0, 325.0, 340.0, 355.0, 377.0, 399.0, 421.0, 442.0),
        ),
        30: (
            (0.922, 0.916, 0.911, 0.906, 0.901, 0.896, 0.891, 0.881, 0.872, 0.863, 0.855, 0.847, 0.839, 0.831, 0.823, 0.813, 0.802, 0.792, 0.782),
            (168.0, 175.0, 182.0, 189.0, 197.0, 204.0, 211.0, 224.0, 238.0, 251.0, 264.0, 277.0, 290.0, 302.0, 314.0, 332.0, 350.0, 367.0, 384.0),
        ),
        40: (
            (0.848, 0.841, 0.834, 0.828, 0.821, 0.815, 0.808, 0.796, 0.784, 0.773, 0.762, 0.751, 0.741, 0.731, 0.721, 0.707, 0.694, 0.681, 0.668),
            (154.0, 161.0, 167.0, 173.0, 179.0, 185.0, 191.0, 203.0, 214.0, 225.0, 235.0, 246.0, 256.0, 266.0, 275.0, 289.0, 303.0, 316.0, 328.0),
        ),
        50: (
            (0.777, 0.768, 0.76, 0.752, 0.744, 0.736, 0.728, 0.713, 0.699, 0.685, 0.672, 0.659, 0.647, 0.635, 0.624, 0.608, 0.592, 0.577, 0.563),
            (141.0, 147.0, 152.0, 157.0, 162.0, 167.0, 172.0, 182.0, 191.0, 199.0, 208.0, 216.0, 224.0, 231.0, 238.0, 249.0, 258.0, 268.0, 277.0),
        ),
        60: (
            (0.707, 0.697, 0.687, 0.678, 0.668, 0.659, 0.651, 0.634, 0.617, 0.602, 0.587, 0.573, 0.56, 0.547, 0.535, 0.517, 0.501, 0.486, 0.471),
            (129.0, 133.0, 137.0, 142.0, 146.0, 150.0, 154.0, 161.0, 168.0, 175.0, 182.0, 188.0, 193.0, 199.0, 204.0, 212.0, 219.0, 225.0, 231.0),
        ),
        70: (
            (0.64, 0.629, 0.618, 0.607, 0.597, 0.587, 0.578, 0.559, 0.542, 0.526, 0.51, 0.496, 0.482, 0.469, 0.456, 0.439, 0.423, 0.408, 0.394),
            (116.0, 120.0, 124.0, 127.0, 130.0, 133.0, 137.0, 142.0, 148.0, 153.0, 158.0, 162.0, 167.0, 171.0, 174.0, 180.0, 184.0, 189.0, 193.0),
        ),
        80: (
            (0.576, 0.564, 0.553, 0.542, 0.531, 0.521, 0.511, 0.492, 0.474, 0.458, 0.442, 0.428, 0.414, 0.402, 0.39, 0.373, 0.358, 0.344, 0.33),
            (105.0, 108.0, 111.0, 113.0, 116.0, 118.0, 121.0, 125.0, 129.0, 133.0, 137.0, 140.0, 143.0, 146.0, 149.0, 153.0, 156.0, 159.0, 162.0),
        ),
        90: (
            (0.517, 0.505, 0.493, 0.482, 0.471, 0.461, 0.451, 0.432, 0.415, 0.399, 0.384, 0.37, 0.357, 0.345, 0.334, 0.319, 0.304, 0.292, 0.28),
            (94.1, 96.4, 98.6, 101.0, 103.0, 105.0, 107.0, 110.0, 113.0, 116.0, 119.0, 121.0, 123.0, 126.0, 128.0, 130.0, 133.0, 135.0, 137.0),
        ),
        100: (
            (0.464, 0.451, 0.44, 0.428, 0.418, 0.408, 0.398, 0.38, 0.363, 0.348, 0.334, 0.321, 0.309, 0.298, 0.288, 0.274, 0.261, 0.249, 0.239),
            (84.3, 86.2, 87.9, 89.6, 91.1, 92.6, 94.0, 96.7, 99.1, 101.0, 103.0, 105.0, 107.0, 108.0, 110.0, 112.0, 114.0, 116.0, 117.0),
        ),
        110: (
            (0.416, 0.404, 0.392, 0.381, 0.371, 0.361, 0.352, 0.335, 0.319, 0.305, 0.292, 0.281, 0.27, 0.259, 0.25, 0.237, 0.226, 0.215, 0.206),
            (75.6, 77.0, 78.4, 79.7, 81.0, 82.1, 83.2, 85.3, 87.1, 88.8, 90.4, 91.8, 93.1, 94.4, 95.5, 97.1, 98.5, 100.0, 101.0),
        ),
        120: (
            (0.373, 0.361, 0.35, 0.34, 0.33, 0.321, 0.313, 0.297, 0.282, 0.269, 0.257, 0.246, 0.236, 0.227, 0.219, 0.207, 0.197, 0.187, 0.179),
            (67.8, 69.0, 70.1, 71.1, 72.1, 73.0, 73.9, 75.5, 77.0, 78.3, 79.5, 80.6, 81.7, 82.6, 83.5, 84.7, 85.8, 86.9, 87.8),
        ),
        130: (
            (0.336, 0.325, 0.314, 0.305, 0.295, 0.287, 0.279, 0.264, 0.251, 0.239, 0.228, 0.218, 0.209, 0.2, 0.193, 0.182, 0.173, 0.164, 0.157),
            (61.0, 62.0, 62.8, 63.7, 64.5, 65.2, 65.9, 67.2, 68.3, 69.4, 70.4, 71.2, 72.1, 72.8, 73.5, 74.5, 75.4, 76.2, 76.9),
        ),
        140: (
            (0.303, 0.292, 0.283, 0.274, 0.265, 0.257, 0.25, 0.236, 0.224, 0.213, 0.203, 0.194, 0.185, 0.178, 0.171, 0.161, 0.153, 0.145, 0.138),
            (55.0, 55.8, 56.5, 57.2, 57.8, 58.4, 59.0, 60.0, 61.0, 61.8, 62.6, 63.3, 64.0, 64.6, 65.2, 66.0, 66.7, 67.3, 67.9),
        ),
        150: (
            (0.274, 0.264, 0.255, 0.247, 0.239, 0.231, 0.224, 0.212, 0.201, 0.19, 0.181, 0.173, 0.165, 0.159, 0.152, 0.144, 0.136, 0.129, 0.123),
            (49.8, 50.4, 51.0, 51.6, 52.1, 52.6, 53.1, 53.9, 54.7, 55.4, 56.0, 56.6, 57.2, 57.7, 58.1, 58.8, 59.3, 59.9, 60.4),
        ),
        160: (
            (0.249, 0.24, 0.231, 0.223, 0.216, 0.209, 0.203, 0.191, 0.181, 0.171, 0.163, 0.155, 0.149, 0.142, 0.137, 0.129, 0.122, 0.116, 0.11),
            (45.2, 45.7, 46.2, 46.7, 47.1, 47.5, 47.9, 48.6, 49.3, 49.9, 50.4, 50.9, 51.3, 51.7, 52.1, 52.7, 53.1, 53.6, 54.0),
        ),
        170: (
            (0.227, 0.218, 0.21, 0.203, 0.196, 0.19, 0.184, 0.173, 0.164, 0.155, 0.147, 0.14, 0.134, 0.128, 0.123, 0.116, 0.11, 0.104, 0.099),
            (41.2, 41.6, 42.1, 42.4, 42.8, 43.1, 43.5, 44.1, 44.6, 45.1, 45.5, 45.9, 46.3, 46.7, 47.0, 47.4, 47.8, 48.2, 48.6),
        ),
        180: (
            (0.207, 0.199, 0.192, 0.185, 0.179, 0.173, 0.167, 0.157, 0.149, 0.141, 0.134, 0.127, 0.122, 0.116, 0.111, 0.105, 0.099, 0.094, 0.089),
            (37.7, 38.0, 38.4, 38.7, 39.0, 39.3, 39.6, 40.1, 40.5, 41.0, 41.3, 41.7, 42.0, 42.3, 42.6, 43.0, 43.3, 43.6, 43.9),
        ),
        190: (
            (0.19, 0.183, 0.176, 0.169, 0.164, 0.158, 0.153, 0.144, 0.136, 0.128, 0.122, 0.116, 0.111, 0.106, 0.101, 0.095, 0.09, 0.085, 0.081),
            (34.5, 34.9, 35.2, 35.4, 35.7, 35.9, 36.2, 36.6, 37.0, 37.4, 37.7, 38.0, 38.2, 38.5, 38.7, 39.1, 39.4, 39.6, 39.9),
        ),
        200: (
            (0.175, 0.168, 0.162, 0.156, 0.15, 0.145, 0.14, 0.132, 0.124, 0.118, 0.112, 0.106, 0.101, 0.097, 0.093, 0.087, 0.082, 0.078, 0.074),
            (31.8, 32.0, 32.3, 32.5, 32.8, 33.0, 33.2, 33.6, 33.9, 34.2, 34.5, 34.7, 35.0, 35.2, 35.4, 35.7, 35.9, 36.2, 36.4),
        ),
        210: (
            (0.161, 0.155, 0.149, 0.143, 0.138, 0.134, 0.129, 0.121, 0.114, 0.108, 0.102, 0.097, 0.093, 0.089, 0.085, 0.08, 0.075, 0.071, 0.068),
            (29.3, 29.6, 29.8, 30.0, 30.2, 30.4, 30.5, 30.9, 31.2, 31.4, 31.7, 31.9, 32.1, 32.3, 32.5, 32.7, 32.9, 33.1, 33.3),
        ),
        220: (
            (0.149, 0.143, 0.138, 0.133, 0.128, 0.123, 0.119, 0.112, 0.105, 0.1, 0.094, 0.09, 0.086, 0.082, 0.078, 0.074, 0.069, 0.066, 0.062),
            (27.1, 27.3, 27.5, 27.7, 27.9, 28.0, 28.2, 28.5, 28.7, 29.0, 29.2, 29.4, 29.6, 29.7, 29.9, 30.1, 30.3, 30.5, 30.6),
        ),
        230: (
            (0.138, 0.133, 0.128, 0.123, 0.118, 0.114, 0.11, 0.104, 0.097, 0.092, 0.087, 0.083, 0.079, 0.075, 0.072, 0.068, 0.064, 0.061, 0.058),
            (25.2, 25.3, 25.5, 25.7, 25.8, 26.0, 26.1, 26.4, 26.6, 26.8, 27.0, 27.1, 27.3, 27.5, 27.6, 27.8, 27.9, 28.1, 28.2),
        ),
        240: (
            (0.129, 0.123, 0.119, 0.114, 0.11, 0.106, 0.103, 0.096, 0.09, 0.085, 0.081, 0.077, 0.073, 0.07, 0.067, 0.063, 0.059, 0.056, 0.053),
            (23.4, 23.6, 23.7, 23.9, 24.0, 24.1, 24.2, 24.5, 24.7, 24.8, 25.0, 25.2, 25.3, 25.4, 25.5, 25.7, 25.9, 26.0, 26.1),
        ),
        250: (
            (0.12, 0.115, 0.11, 0.106, 0.102, 0.099, 0.095, 0.089, 0.084, 0.079, 0.075, 0.071, 0.068, 0.065, 0.062, 0.058, 0.055, 0.052, 0.049),
            (21.8, 22.0, 22.1, 22.2, 22.3, 22.5, 22.6, 22.8, 22.9, 23.1, 23.2, 23.4, 23.5, 23.6, 23.7, 23.9, 24.0, 24.1, 24.2),
        ),
    },
}
