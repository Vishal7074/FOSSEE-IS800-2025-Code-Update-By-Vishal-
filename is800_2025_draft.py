"""Steel design helpers for review against BIS CED 07 (27869) WC, April 2025.
Units: N, mm, MPa, N mm. This is an educational draft implementation.
The accompanying migration register identifies unresolved and omitted cases.
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
    """Select a draft calculation explicitly. No automatic legacy fallback."""

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
    def tube_class(diameter, thickness, fy, *, loading):
        """Table 2(vi). Outside diameter. Axial row has only a Class 3 limit."""
        _positive(diameter, thickness, fy)
        limits = {"moment": (47, 66, 85), "axial": (None, None, 86)}
        return _classify(diameter/thickness, limits[loading], 250/fy)

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
