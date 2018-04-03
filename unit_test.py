import unittest
from cspm_utils import find_pokemon_id, get_team_id, get_team_name, get_team_color, get_egg_url
from cspm_utils import MYSTIC_COLOR, VALOR_COLOR, INSTINCT_COLOR, UNKNOWN_COLOR
from cspm_utils import LEVEL_1_2_EGG_URL, LEVEL_3_4_EGG_URL, LEVEL_5_EGG_URL

'''
Run with: python3 unit_test.py
'''
class TestCSPM(unittest.TestCase):

    def test_find_pokemon_id(self):
        # Valid
        self.assertEqual(find_pokemon_id('Bulbasaur'), 1)
        self.assertEqual(find_pokemon_id('Ho-Oh'), 250)
        self.assertEqual(find_pokemon_id('Lugia'), 249)
        self.assertEqual(find_pokemon_id('Egg'), 0)

        # Invalid
        self.assertEqual(find_pokemon_id('missingno'), 0)
        self.assertEqual(find_pokemon_id('bulbasaur'), 0)
        self.assertEqual(find_pokemon_id('ho-Oh'), 0)
        self.assertEqual(find_pokemon_id('egg'), 0)

    def test_get_team_id(self):
        self.assertEqual(get_team_id("0"), 0)
        self.assertEqual(get_team_id("1"), 1)
        self.assertEqual(get_team_id("2"), 2)
        self.assertEqual(get_team_id("3"), 3)
        self.assertEqual(get_team_id("4"), 0)

        self.assertEqual(get_team_id("Mystic"), 1)
        self.assertEqual(get_team_id("Valor"), 2)
        self.assertEqual(get_team_id("Instinct"), 3)

        self.assertEqual(get_team_id("mystic"), 1)
        self.assertEqual(get_team_id("Blue"), 1)
        self.assertEqual(get_team_id("blue"), 1)

        self.assertEqual(get_team_id("blah"), 0)

    def test_get_team_name(self):
        self.assertEqual(get_team_name(0), 'Unknown')
        self.assertEqual(get_team_name(1), 'Mystic')
        self.assertEqual(get_team_name(2), 'Valor')
        self.assertEqual(get_team_name(3), 'Instinct')
        self.assertEqual(get_team_name(4), 'Unknown')

    def test_get_team_color(self):
        self.assertEqual(get_team_color(0), UNKNOWN_COLOR)
        self.assertEqual(get_team_color(1), MYSTIC_COLOR)
        self.assertEqual(get_team_color(2), VALOR_COLOR)
        self.assertEqual(get_team_color(3), INSTINCT_COLOR)
        self.assertEqual(get_team_color(4), UNKNOWN_COLOR)

    def test_get_egg_url(self):
        self.assertEqual(get_egg_url('0'), LEVEL_5_EGG_URL)
        self.assertEqual(get_egg_url('1'), LEVEL_1_2_EGG_URL)
        self.assertEqual(get_egg_url('2'), LEVEL_1_2_EGG_URL)
        self.assertEqual(get_egg_url('3'), LEVEL_3_4_EGG_URL)
        self.assertEqual(get_egg_url('4'), LEVEL_3_4_EGG_URL)
        self.assertEqual(get_egg_url('5'), LEVEL_5_EGG_URL)
        self.assertEqual(get_egg_url('6'), LEVEL_5_EGG_URL)

if __name__ == '__main__':
    unittest.main()
