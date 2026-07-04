#!/usr/bin/env python3
"""
Tests unitaires pour la classe TableReport (RelID - Gramps).
"""

import unittest
import os
import tempfile
from unittest.mock import MagicMock, patch, mock_open

# Mock des dépendances GTK et autres
import sys
import types
gtk_mock = types.ModuleType('gi.repository')
gtk_mock.Gtk = MagicMock()
gtk_mock.Gdk = MagicMock()
gtk_mock.GObject = MagicMock()
sys.modules['gi.repository'] = gtk_mock
sys.modules['gi.repository.Gtk'] = gtk_mock.Gtk
sys.modules['gi.repository.Gdk'] = gtk_mock.Gdk
sys.modules['gi.repository.GObject'] = gtk_mock.GObject

# Ajout du chemin pour importer les modules Gramps et RelID
sys.path.insert(0, os.path.join(os.environ.get('GRAMPS_DIR', ''), 'gramps'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from relation_tab import TableReport

# ============================================================================
# CLASSES MOCK POUR LES DÉPENDANCES
# ============================================================================

class MockODSTab:
    """Mock de la classe ODSTab pour éviter les dépendances externes."""
    def __init__(self, rows):
        self.rows = rows
        self.file = None
        self.opened = False

    def open(self, filename):
        self.file = filename
        self.opened = True

    def start_page(self):
        pass

    def end_page(self):
        pass

    def close(self):
        self.opened = False

    def creator(self, name):
        pass

# ============================================================================
# TESTS POUR TableReport
# ============================================================================

class TestTableReport(unittest.TestCase):
    def setUp(self):
        """Initialise les objets nécessaires pour chaque test."""
        # Créer un fichier temporaire pour les tests
        self.temp_dir = tempfile.TemporaryDirectory()
        self.filename = os.path.join(self.temp_dir.name, "test_output.ods")

        # Mock de ODSTab
        self.mock_ods_tab = MockODSTab(10)
        self.table_report = TableReport(self.filename, self.mock_ods_tab)

        # Données de test
        self.titles = [
            ("Rel_id", 0, 40, int),
            ("Relation", 1, 300, str),
            ("Name", 2, 200, str),
        ]
        self.sample_data = [
            (1, "Parent", "John Doe"),
            (2, "Child", "Jane Doe"),
            (3, "Grandparent", "Alice Smith"),
        ]

    def tearDown(self):
        """Nettoie les ressources après chaque test."""
        self.temp_dir.cleanup()

    # ========================================================================
    # TESTS D'INITIALISATION
    # ========================================================================

    def test_initialization(self):
        """Teste que TableReport est correctement initialisé."""
        self.assertEqual(self.table_report.filename, self.filename)
        self.assertEqual(self.table_report.doc, self.mock_ods_tab)
        self.assertFalse(self.mock_ods_tab.opened)

    # ========================================================================
    # TESTS POUR initialize
    # ========================================================================

    def test_initialize(self):
        """Teste l'initialisation du document ODS."""
        self.table_report.initialize(len(self.titles))
        self.assertTrue(self.mock_ods_tab.opened)
        self.assertEqual(self.mock_ods_tab.file, self.filename)

    def test_initialize_with_zero_columns(self):
        """Teste l'initialisation avec 0 colonnes."""
        with self.assertRaises(ValueError):
            self.table_report.initialize(0)

    # ========================================================================
    # TESTS POUR write_table_head
    # ========================================================================

    def test_write_table_head(self):
        """Teste l'écriture des en-têtes du tableau."""
        self.table_report.initialize(len(self.titles))
        self.table_report.write_table_head(self.titles)
        # Pas d'erreur = succès (méthode mockée)
        self.assertTrue(True)

    def test_write_table_head_empty_titles(self):
        """Teste l'écriture des en-têtes avec une liste vide."""
        self.table_report.initialize(0)
        with self.assertRaises(ValueError):
            self.table_report.write_table_head([])

    # ========================================================================
    # TESTS POUR set_row
    # ========================================================================

    def test_set_row_even(self):
        """Teste la définition d'une ligne paire (0)."""
        self.table_report.set_row(0)
        # Pas d'erreur = succès
        self.assertTrue(True)

    def test_set_row_odd(self):
        """Teste la définition d'une ligne impaire (1)."""
        self.table_report.set_row(1)
        # Pas d'erreur = succès
        self.assertTrue(True)

    # ========================================================================
    # TESTS POUR write_table_data
    # ========================================================================

    def test_write_table_data(self):
        """Teste l'écriture des données du tableau."""
        self.table_report.initialize(len(self.titles))
        self.table_report.write_table_head(self.titles)
        for entry in self.sample_data:
            self.table_report.write_table_data(entry)
        # Pas d'erreur = succès
        self.assertTrue(True)

    def test_write_table_data_empty_entry(self):
        """Teste l'écriture d'une entrée vide."""
        self.table_report.initialize(len(self.titles))
        self.table_report.write_table_head(self.titles)
        with self.assertRaises(ValueError):
            self.table_report.write_table_data(())

    # ========================================================================
    # TESTS POUR finalize
    # ========================================================================

    def test_finalize(self):
        """Teste la finalisation du document ODS."""
        self.table_report.initialize(len(self.titles))
        self.table_report.finalize()
        self.assertFalse(self.mock_ods_tab.opened)

    # ========================================================================
    # TESTS D'INTÉGRATION (INITIALIZE + WRITE + FINALIZE)
    # ========================================================================

    def test_full_workflow(self):
        """Teste le workflow complet : initialisation, écriture, finalisation."""
        # 1. Initialisation
        self.table_report.initialize(len(self.titles))

        # 2. Écriture des en-têtes
        self.table_report.write_table_head(self.titles)

        # 3. Écriture des données
        for index, entry in enumerate(self.sample_data):
            self.table_report.set_row(index % 2)
            self.table_report.write_table_data(entry)

        # 4. Finalisation
        self.table_report.finalize()

        # Vérifications
        self.assertFalse(self.mock_ods_tab.opened)

    # ========================================================================
    # TESTS AVEC MOCKS POUR LES FICHIERS
    # ========================================================================

    @patch('builtins.open', new_callable=mock_open)
    def test_file_operations(self, mock_file):
        """Teste les opérations de fichier avec des mocks."""
        # Initialisation
        self.table_report.initialize(len(self.titles))

        # Écriture des en-têtes
        self.table_report.write_table_head(self.titles)

        # Écriture des données
        for entry in self.sample_data:
            self.table_report.write_table_data(entry)

        # Finalisation
        self.table_report.finalize()

        # Vérifier que le fichier a été "ouvert" et "fermé"
        mock_file.assert_called_with(self.filename, 'wb')

    # ========================================================================
    # TESTS POUR LES ERREURS
    # ========================================================================

    def test_initialize_with_invalid_filename(self):
        """Teste l'initialisation avec un nom de fichier invalide."""
        invalid_table_report = TableReport("", self.mock_ods_tab)
        with self.assertRaises(ValueError):
            invalid_table_report.initialize(len(self.titles))

    def test_write_table_data_with_wrong_number_of_columns(self):
        """Teste l'écriture de données avec un nombre incorrect de colonnes."""
        self.table_report.initialize(2)  # 2 colonnes attendues
        with self.assertRaises(ValueError):
            self.table_report.write_table_data((1, "Parent", "John Doe"))  # 3 colonnes fournies

# ============================================================================
# EXÉCUTION DES TESTS
# ============================================================================

if __name__ == "__main__":
    unittest.main()
