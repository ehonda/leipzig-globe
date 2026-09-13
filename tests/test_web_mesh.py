"""Check the rendered triangle surface, not just vertices on the sphere."""

import math

import numpy as np
import pytest

from leipzig_globe.config import validate_config
from leipzig_globe.printing import _outline
from leipzig_globe.web_preview import _export_gore


@pytest.mark.parametrize("count", [4, 12, 24])
@pytest.mark.parametrize("diameter,overlap", [(215, 2), (300, 0), (215, 10)])
@pytest.mark.parametrize("order", ["clockwise", "counterclockwise"])
def test_surface_uvs_seams_and_overlaps(count, diameter, overlap, order):
    config = validate_config(
        {
            "globe": {
                "diameter_mm": diameter,
                "gore_count": count,
                "assembly_overlap_mm": overlap,
            },
            "layout": {"gore_order": order},
        }
    )
    circumference = math.pi * diameter
    width, height = circumference / count, circumference / 2
    outline, seam = _outline(width, height, overlap)
    exports = {}
    for index in range(count):
        slot = index if order == "clockwise" else count - 1 - index
        gore = {
            "index": index,
            "longitude_slot": slot,
            "png": "gore.png",
            "width_mm": width + overlap + 6,
            "height_mm": height + 6,
            "inset_mm": 3,
            "equator_width_mm": width,
            "pole_to_pole_mm": height,
            "overlap_equator_mm": overlap,
            "outline_mm": outline,
            "seam_mm": seam,
        }
        exported = _export_gore(gore, config)
        exports[slot] = exported
        for key in ("mesh", "overlap_mesh"):
            mesh = exported[key]
            positions = np.asarray(mesh["positions"]).reshape(-1, 3)
            uvs = np.asarray(mesh["uvs"]).reshape(-1, 2)
            triangles = positions[np.asarray(mesh["indices"]).reshape(-1, 3)]
            np.testing.assert_allclose(np.linalg.norm(positions, axis=1), 1, atol=1e-12)
            # Sample centroids and all edge midpoints, including polar degeneracies.
            for weights in ([1 / 3] * 3, [0.5, 0.5, 0], [0, 0.5, 0.5], [0.5, 0, 0.5]):
                interior = np.einsum("tvc,v->tc", triangles, weights)
                assert np.max(1 - np.linalg.norm(interior, axis=1)) < 0.001
            # Plane distance is a conservative lower bound on the radius of
            # EVERY point inside each nondegenerate triangle, not just samples.
            normals = np.cross(
                triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]
            )
            lengths = np.linalg.norm(normals, axis=1)
            valid = lengths > 1e-14
            distances = (
                np.abs(np.einsum("tc,tc->t", normals[valid], triangles[valid, 0]))
                / lengths[valid]
            )
            if len(distances):
                assert np.min(distances) > 0.999
                # Outward winding is needed for correct normals and lighting.
                assert np.all(
                    np.einsum("tc,tc->t", normals[valid], triangles[valid, 0]) > 0
                )
            # Independently invert the printed-image UVs back to paper and then
            # use the print renderer's latitude/longitude sampling equations.
            assert np.all((uvs >= 0) & (uvs <= 1))
            y = (1 - uvs[:, 1]) * gore["height_mm"] - 3
            x = uvs[:, 0] * gore["width_mm"] - 3 - width / 2
            taper = np.sin(math.pi * y / height)
            away = np.abs(taper) > 1e-10
            longitude = (
                2
                * math.pi
                * ((slot + 0.5) / count + x[away] / (circumference * taper[away]))
            )
            expected = np.column_stack(
                (
                    taper[away] * np.sin(longitude),
                    np.cos(math.pi * y[away] / height),
                    taper[away] * np.cos(longitude),
                )
            )
            np.testing.assert_allclose(positions[away], expected, atol=1e-11)
        surface = np.asarray(exported["mesh"]["positions"]).reshape(121, -1, 3)
        band = np.asarray(exported["overlap_mesh"]["positions"]).reshape(121, -1, 3)
        np.testing.assert_allclose(surface[:, -1], band[:, -1], atol=1e-12)
        np.testing.assert_allclose(
            band[:, 0], np.asarray(exported["nominal_seam"]).reshape(-1, 3), atol=1e-12
        )
    for slot, exported in exports.items():
        neighbor = np.asarray(exports[(slot + 1) % count]["mesh"]["positions"]).reshape(
            121, -1, 3
        )
        np.testing.assert_allclose(
            np.asarray(exported["nominal_seam"]).reshape(-1, 3),
            neighbor[:, 0],
            atol=1e-12,
        )
