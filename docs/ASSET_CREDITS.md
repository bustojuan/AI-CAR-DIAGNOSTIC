# Asset credits and redistribution

The root MIT license covers application code and original documentation, not
third-party images/models or dependencies. This educational publication retains
separate notices. It is **not an unrestricted commercial asset bundle**.

| Asset | Author / source | License and redistribution scope |
| --- | --- | --- |
| `frontend/public/models/golf-viii-gti.glb` | Mona x Supercars / [Car2022](https://sketchfab.com/Car2022); embedded GT Cars: Hyperspeed credit. [Original Volkswagen Golf 8. GTI (A8)](https://sketchfab.com/3d-models/e87d7c0f8937481db236529beb5ecab7), distributed by [pedrosoandre/carros](https://github.com/pedrosoandre/carros). | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/): attribution, source/license links and change notices required; permits commercial redistribution subject to terms and other applicable rights. |
| `golf-viii-gti-poster.png` | Application render of the same GLB | Retain the same CC BY attribution. Render is derived; GLB is unchanged from distributor. |
| `golf-2006-tdi-bew-engine-bay.jpg` | **VW TDI**, [under hood - overview](https://www.flickr.com/photos/vw_tdi/192839547/) | [CC BY-NC-SA 2.0](https://creativecommons.org/licenses/by-nc-sa/2.0/): non-commercial sharing, attribution and same-license adaptations. No unrestricted commercial/marketing permission is asserted. |
| Photo location annotations in `photo.ts` | Project annotations derived from the VW TDI photograph | CC BY-NC-SA 2.0, same photo source/credit. Coordinates identify only this reference image. |
| `automotive-features.png` | Project-generated, AI-assisted decorative engine/manual/brake atlas; recorded as generated in development provenance | Project-provided decorative asset. Not a real parts catalog, technical source or manufacturer endorsement. No third-party stock-photo license is claimed. |
| Favicon, architecture diagrams, authored CSS | Motor contributors | Original project assets under MIT. |
| Lucide icons | Lucide contributors; some derived Feather icons by Cole Bemis | ISC / applicable MIT notices, preserved in [LUCIDE-LICENSE.txt](licenses/LUCIDE-LICENSE.txt). |
| UI fonts | Local OS system fonts | No font binary is redistributed; browser uses the system fallback stack. |
| Browser screenshots | Actual application captures; synthetic data | Project UI under MIT; model/photo material retains its own rights. The Engine Bay screenshot/photographic annotations retain CC BY-NC-SA 2.0; preserve this attribution with redistribution. |

The GLB contains its source, author and CC BY license metadata. The repository
preserves [full CC BY terms](../frontend/public/models/CC-BY-4.0.txt),
[prior distributor changes](../frontend/public/models/GOLF-DISTRIBUTOR-LICENSE.md)
and [photo source/license details](../frontend/public/images/golf-2006-tdi-bew-engine-bay.LICENSE.txt).
The viewer's info panel and Settings retain model attribution and applicability;
the Engine Bay image retains visible photo attribution/license and illustration
warning. These notices must not be stripped from redistributed derivatives.

The photo is not Golf Plus/CFFB: it depicts a Golf 2006 **1.9 TDI BEW**. The exterior
is a Golf VIII GTI, not an exact Golf Plus. Neither establishes part compatibility,
installed component positions or repair correctness. No endorsement is implied.

For commercial use, replace the NC photograph/annotations and its derived screenshot
with properly cleared material or obtain separate permission from the rights holder.
Do not assume that a portfolio, employment or promotional use is automatically
non-commercial; assess the intended use against the license. This copy is prepared
as a non-commercial educational repository and makes no broader rights guarantee.

Dependencies are pinned in package/uv locks and retain their package licenses;
React, Three.js/R3F/Drei and the remaining npm/Python packages are dependencies,
not re-licensed here. Their installed distributions must retain their notices.
In particular, PyMuPDF has AGPL/commercial terms and psycopg is LGPL; see the
[dependency licensing review](licenses/DEPENDENCY_NOTICES.md). MIT does not
grant blanket permission for the combined application.
No node_modules, vendored framework code, old Car Concept model, unused Golf Plus
studio image, workshop manual or copyrighted document extracts are bundled.
