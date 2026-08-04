import copy
import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "validate-routing-spec.py"
SPEC = importlib.util.spec_from_file_location("validate_routing_spec", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class RoutingSpecValidatorTest(unittest.TestCase):
    def routing_spec(self):
        return MODULE.load_spec(ROOT)

    def test_committed_routing_spec_is_valid(self):
        self.assertEqual([], MODULE.validate(ROOT, self.routing_spec()))

    def test_duplicate_route_ids_are_rejected(self):
        spec = self.routing_spec()
        spec["routes"].append(copy.deepcopy(spec["routes"][0]))
        errors = MODULE.validate(ROOT, spec)
        self.assertTrue(any("duplicate route id" in error for error in errors))

    def test_bounded_routes_require_an_opaque_boundary(self):
        spec = self.routing_spec()
        spec["routes"][0]["opaqueBoundary"] = None
        errors = MODULE.validate(ROOT, spec)
        self.assertTrue(any("requires opaqueBoundary" in error for error in errors))

    def test_complete_routes_cannot_contain_unknown_targets(self):
        spec = self.routing_spec()
        direct = next(route for route in spec["routes"] if route["id"] == "public.direct.id0.main")
        direct["target"]["sensorScenario"] = "UNKNOWN"
        errors = MODULE.validate(ROOT, spec)
        self.assertTrue(any("cannot contain unknown" in error for error in errors))

    def test_unavailable_routes_require_a_valid_fallback(self):
        spec = self.routing_spec()
        unavailable = next(
            route for route in spec["routes"] if route["id"] == "replacement.ultrawide.request"
        )
        unavailable["fallback"]["routeId"] = "missing.route"
        errors = MODULE.validate(ROOT, spec)
        self.assertTrue(any("references unknown route" in error for error in errors))

    def test_digital_routes_cannot_claim_auxiliary_optics(self):
        spec = self.routing_spec()
        digital = next(route for route in spec["routes"] if route["id"] == "public.zoom.id0.digital")
        digital["target"]["opticalRoute"] = "telephoto"
        errors = MODULE.validate(ROOT, spec)
        self.assertTrue(any("cannot claim an auxiliary optical route" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
