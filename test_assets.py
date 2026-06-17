import unittest

from assets import (
    brand_color,
    flag_code_from_country,
    logo_slug_from_car,
    static_relpath,
)
from wec_data import HYPERCAR_TEAMS, LMGT3_TEAMS, build_grid


class LogoSlugTests(unittest.TestCase):
    def test_hypercar_manufacturers(self):
        expected = {
            "Toyota GR010 Hybrid": "toyota",
            "Ferrari 499P": "ferrari",
            "Porsche 963": "porsche",
            "Cadillac V-Series.R": "cadillac",
            "BMW M Hybrid V8": "bmw",
            "Peugeot 9X8": "peugeot",
            "Alpine A424": "alpine",
            "Lamborghini SC63": "lamborghini",
        }
        for team in HYPERCAR_TEAMS:
            self.assertEqual(logo_slug_from_car(team["car"]), expected[team["car"]])

    def test_lmgt3_manufacturers(self):
        samples = {
            "Aston Martin Vantage": "aston-martin",
            "Ferrari 296 GT3": "ferrari",
            "Porsche 911 GT3 R": "porsche",
            "McLaren 720S GT3 Evo": "mclaren",
            "Lexus RC F GT3": "lexus",
            "Ford Mustang GT3": "ford",
            "BMW M4 GT3 Evo": "bmw",
            "Corvette Z06 GT3.R": "chevrolet",
            "Lamborghini Huracán GT3": "lamborghini",
            "Mercedes-AMG GT3": "mercedes",
        }
        for car, slug in samples.items():
            self.assertEqual(logo_slug_from_car(car), slug)

    def test_grid_teams_include_logo_slug(self):
        teams, _ = build_grid()
        self.assertEqual(len(teams), len(HYPERCAR_TEAMS) + len(LMGT3_TEAMS))
        for team in teams:
            self.assertIn("logo_slug", team)
            self.assertEqual(team["logo_slug"], logo_slug_from_car(team["car"]))

    def test_flag_codes(self):
        self.assertEqual(flag_code_from_country("France"), "fr")
        self.assertEqual(flag_code_from_country("United States"), "us")
        self.assertEqual(flag_code_from_country(""), "")

    def test_brand_color_known_slug(self):
        self.assertEqual(brand_color("ferrari"), "#DC0000")

    def test_static_relpath_for_bundled_logo(self):
        self.assertEqual(static_relpath("logo", "toyota"), "img/logos/toyota.svg")
        self.assertIsNone(static_relpath("logo", "nonexistent-brand"))


if __name__ == "__main__":
    unittest.main()
