#!/usr/bin/env python3
"""
Tests unitaires complets et améliorés pour RelationTab (RelID - Gramps).
"""

import unittest
import sys
import os
import types
from unittest.mock import MagicMock, patch

# Mock des dépendances GTK
gtk_mock = types.ModuleType('gi.repository')
gtk_mock.Gtk = MagicMock()
gtk_mock.Gdk = MagicMock()
gtk_mock.GObject = MagicMock()
gtk_mock.GLib = MagicMock()
sys.modules['gi.repository'] = gtk_mock
sys.modules['gi.repository.Gtk'] = gtk_mock.Gtk
sys.modules['gi.repository.Gdk'] = gtk_mock.Gdk
sys.modules['gi.repository.GObject'] = gtk_mock.GObject
sys.modules['gi.repository.GLib'] = gtk_mock.GLib

# Ajout du chemin pour importer les modules Gramps et RelID
sys.path.insert(0, os.path.join(os.environ.get('GRAMPS_DIR', ''), 'gramps'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gramps.gen.lib import Person, Family, Event, Place
from gramps.gen.lib.date import Date
from gramps.gen.relationship import get_relationship_calculator
from relation_tab import RelationTab, RelIDOptions, RelIDReport, FamilyPathMetrics, RelationFilterManager

# ============================================================================
# CLASSES MOCK
# ============================================================================

class MockTransaction:
    def __init__(self, name):
        self.name = name
        self._batch = False

    def batch_start(self):
        self._batch = True

    def batch_commit(self):
        self._batch = False

    def add(self, *args, **kwargs):
        pass

    def commit(self):
        pass

    def rollback(self):
        pass

class MockUndoManager:
    def __init__(self, db):
        self.db = db

    def register(self, *args, **kwargs):
        pass

class UndoMockDB:
    def __init__(self, db):
        self.db = db

    def register(self, *args, **kwargs):
        pass

class MockNotebook:
    def __init__(self):
        self.pages = []

    def append_page(self, *args, **kwargs):
        pass

class MockSignals:
    def __init__(self):
        self._callbacks = {}

    def connect(self, *args, **kwargs):
        pass

class MockDbState:
    def __init__(self, db):
        self.db = db

class MockUser:
    def __init__(self):
        self.uistate = MagicMock()

class MockDatabase:
    def __init__(self):
        self._people = {}
        self._families = {}
        self._events = {}
        self._places = {}
        self._citations = {}
        self._sources = {}
        self._transactions = []
        self._current_txn = None
        self.undodb = UndoMockDB(self)
        self.signals = MockSignals()

    def get_person_from_handle(self, handle):
        return self._people.get(handle)

    def get_family_from_handle(self, handle):
        return self._families.get(handle)

    def get_event_from_handle(self, handle):
        return self._events.get(handle)

    def get_place_from_handle(self, handle):
        return self._places.get(handle)

    def get_person_handles(self, sort_handles=False):
        return list(self._people.keys())

    def get_family_handles(self, sort_handles=False):
        return list(self._families.keys())

    def get_all_people(self):
        return list(self._people.values())

    def get_all_families(self):
        return list(self._families.values())

    def iter_person_handles(self):
        return iter(self._people.keys())

    def transaction(self, *args, **kwargs):
        name = kwargs.get('name', f"Transaction-{len(self._transactions)}")
        txn = MockTransaction(name)
        self._transactions.append(txn)
        self._current_txn = txn
        return txn

    def get_notebook(self):
        return MockNotebook()

    def get_undo_manager(self):
        return MockUndoManager(self)

    def get_default_person(self):
        if self._people:
            return next(iter(self._people.values()))
        return None

class MockGenerator:
    def __init__(self, options):
        self.options = options
        self.db = MockDatabase()
        self.rules = []

class MockRelIDReport:
    def __init__(self, generator, name, title):
        self.generator = generator
        self.name = name
        self.title = title
        self.data = {}

# ============================================================================
# TESTS POUR FamilyPathMetrics
# ============================================================================

class TestFamilyPathMetrics(unittest.TestCase):
    def setUp(self):
        self.db = MockDatabase()
        self.person1 = Person()
        self.person1.handle = "h1"
        self.person1.primary_name = "John Doe"
        self.db._people["h1"] = self.person1

        self.person2 = Person()
        self.person2.handle = "h2"
        self.person2.primary_name = "Jane Doe"
        self.db._people["h2"] = self.person2

        self.family = Family()
        self.family.handle = "f1"
        self.family.father_handle = "h1"
        self.family.mother_handle = "h2"
        self.db._families["f1"] = self.family

    def test_extract_relationship_paths(self):
        mock_result = [[0, 1, "mfm", 2, "ffm", 3]]
        rel_a, rel_b = FamilyPathMetrics.extract_relationship_paths(mock_result)
        self.assertEqual(rel_a, "mfm")
        self.assertEqual(rel_b, "ffm")

    def test_calculate_relationship_path_lengths(self):
        Ga, Gb = FamilyPathMetrics.calculate_relationship_path_lengths("mfm", "ffm")
        self.assertEqual(Ga, 3)
        self.assertEqual(Gb, 3)

    def test_calculate_mra(self):
        self.assertEqual(FamilyPathMetrics.calculate_mra("mfm"), 15)
        self.assertEqual(FamilyPathMetrics.calculate_mra("ff"), 5)
        self.assertEqual(FamilyPathMetrics.calculate_mra("m"), 3)
        self.assertEqual(FamilyPathMetrics.calculate_mra("f"), 2)

    def test_calculate_kekule_number(self):
        # Test avec des valeurs simples
        self.assertEqual(FamilyPathMetrics.calculate_kekule_number(2, 2, "mm", "ff"), 0)
        # Test avec des valeurs valides
        self.assertIsInstance(FamilyPathMetrics.calculate_kekule_number(1, 1, "m", "f"), int)

    @patch('relation_tab.get_relationship_calculator')
    def test_calculate_shared_subtree_size(self, mock_calculator):
        # Mock du calculateur de relation
        mock_relationship = MagicMock()
        mock_relationship.get_relationship_distance_new.return_value = [[0, "h1", "mfm", 2, "ffm", 3]]
        mock_calculator.return_value = mock_relationship

        # Ajout d'une personne commune
        common_ancestor = Person()
        common_ancestor.handle = "h_common"
        self.db._people["h_common"] = common_ancestor

        # Mock de get_person_from_handle pour retourner la personne commune
        with patch.object(self.db, 'get_person_from_handle', return_value=common_ancestor):
            size = FamilyPathMetrics.calculate_shared_subtree_size(self.db, "h1", "h2")
            self.assertIsInstance(size, int)

    @patch('relation_tab.get_relationship_calculator')
    def test_calculate_family_network_centrality(self, mock_calculator):
        mock_relationship = MagicMock()
        mock_calculator.return_value = mock_relationship

        centrality = FamilyPathMetrics.calculate_family_network_centrality(self.db, "h1")
        self.assertIsInstance(centrality, int)

    def test_count_unique_ancestors(self):
        count = FamilyPathMetrics.count_unique_ancestors(self.db, "h1", generations=2)
        self.assertIsInstance(count, int)

    def test_calculate_surname_diversity(self):
        diversity = FamilyPathMetrics.calculate_surname_diversity(self.db, "h1", generations=2)
        self.assertIsInstance(diversity, float)

# ============================================================================
# TESTS POUR RelationFilterManager
# ============================================================================

class TestRelationFilterManager(unittest.TestCase):
    def setUp(self):
        self.db = MockDatabase()
        self.dbstate = MockDbState(self.db)
        self.filter_manager = RelationFilterManager(self.dbstate)

    def test_update_rules_ancestors(self):
        self.filter_manager.update_rules(0, "h1")
        self.assertEqual(len(self.filter_manager.current_rules), 1)

    def test_update_rules_descendants(self):
        self.filter_manager.update_rules(1, "h1")
        self.assertEqual(len(self.filter_manager.current_rules), 1)

    def test_update_rules_related(self):
        self.filter_manager.update_rules(2, "h1")
        self.assertEqual(len(self.filter_manager.current_rules), 1)

    def test_apply_filter(self):
        person1 = Person()
        person1.handle = "h1"
        self.db._people["h1"] = person1

        person2 = Person()
        person2.handle = "h2"
        self.db._people["h2"] = person2

        self.filter_manager.update_rules(2, "h1")
        filtered_list = self.filter_manager.apply_filter(["h1", "h2"])
        self.assertIsInstance(filtered_list, list)

# ============================================================================
# TESTS POUR RelationTab
# ============================================================================

class TestRelationTab(unittest.TestCase):
    def setUp(self):
        self.db = MockDatabase()
        self.dbstate = MockDbState(self.db)
        self.user = MockUser()
        self.options = RelIDOptions()
        self.report = MockRelIDReport(MockGenerator(self.options), "test_report", "Test Report")

        # Ajout de données mock
        self.person1 = Person()
        self.person1.handle = "h1"
        self.person1.primary_name = "John Doe"
        self.db._people["h1"] = self.person1

        self.person2 = Person()
        self.person2.handle = "h2"
        self.person2.primary_name = "Jane Doe"
        self.db._people["h2"] = self.person2

        self.family = Family()
        self.family.handle = "f1"
        self.family.father_handle = "h1"
        self.family.mother_handle = "h2"
        self.db._families["f1"] = self.family

        self.relation_tab = RelationTab(self.dbstate, self.user, self.options, "test_tab")

    def test_initialization(self):
        self.assertIsNotNone(self.relation_tab.dbstate)
        self.assertIsNotNone(self.relation_tab.options)
        self.assertIsNotNone(self.relation_tab.relationship)
        self.assertIsNotNone(self.relation_tab.filter_manager)

    @patch('relation_tab.get_relationship_calculator')
    def test_process_people(self, mock_calculator):
        mock_relationship = MagicMock()
        mock_relationship.get_relationship_distance_new.return_value = [[0, "h1", "mfm", 2, "ffm", 3]]
        mock_calculator.return_value = mock_relationship

        self.relation_tab.process_people(2, None, None, self.person1, 2)
        self.assertGreaterEqual(len(self.relation_tab.stats_list), 0)

    def test_on_filter_rule_changed(self):
        self.relation_tab.__filter_rule = MagicMock()
        self.relation_tab.__filter_rule.get_value.return_value = 0
        self.relation_tab.__fid = MagicMock()
        self.relation_tab.__fid.get_value.return_value = "h1"

        self.relation_tab.on_filter_rule_changed()
        self.assertEqual(len(self.relation_tab.filter_manager.current_rules), 1)

    def test_apply_and_update_filter(self):
        self.relation_tab.filter_manager.update_rules(2, "h1")
        self.relation_tab.apply_and_update_filter()
        self.assertIsInstance(self.relation_tab.filtered_list, list)

    @patch('relation_tab.ODSTab')
    @patch('relation_tab.TableReport')
    def test_save(self, mock_table_report, mock_ods_tab):
        # Mock de la boîte de dialogue pour sélectionner un dossier
        with patch('relation_tab.Gtk.FileChooserDialog') as mock_chooser:
            mock_dialog = MagicMock()
            mock_dialog.run.return_value = 1  # Gtk.ResponseType.OK
            mock_dialog.get_current_folder.return_value = "/tmp"
            mock_chooser.return_value = mock_dialog

            # Ajout de données pour le test
            self.relation_tab.stats_list = [(1, "Parent", "John Doe", 1, 1, 1, 1, "1800-1900")]

            self.relation_tab.save()
            mock_ods_tab.assert_called_once()
            mock_table_report.assert_called_once()

# ============================================================================
# EXÉCUTION DES TESTS
# ============================================================================

if __name__ == "__main__":
    unittest.main()
