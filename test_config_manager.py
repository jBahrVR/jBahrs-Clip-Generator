import unittest
from unittest.mock import patch
import os
import config_manager

class TestConfigManager(unittest.TestCase):

    @patch('os.getenv')
    @patch('os.path.exists')
    @patch('os.makedirs')
    def test_get_app_data_path_with_appdata_dir_not_exists(self, mock_makedirs, mock_exists, mock_getenv):
        # Setup mocks
        mock_getenv.return_value = '/fake/appdata'
        mock_exists.return_value = False

        # Call function
        result = config_manager.get_app_data_path()

        # Assertions
        expected_path = os.path.join('/fake/appdata', 'jBahrsClipGenerator')
        self.assertEqual(result, expected_path)
        mock_getenv.assert_called_once_with('APPDATA')
        mock_exists.assert_called_once_with(expected_path)
        mock_makedirs.assert_called_once_with(expected_path)

    @patch('os.getenv')
    @patch('os.path.exists')
    @patch('os.makedirs')
    def test_get_app_data_path_with_appdata_dir_exists(self, mock_makedirs, mock_exists, mock_getenv):
        # Setup mocks
        mock_getenv.return_value = '/fake/appdata'
        mock_exists.return_value = True

        # Call function
        result = config_manager.get_app_data_path()

        # Assertions
        expected_path = os.path.join('/fake/appdata', 'jBahrsClipGenerator')
        self.assertEqual(result, expected_path)
        mock_getenv.assert_called_once_with('APPDATA')
        mock_exists.assert_called_once_with(expected_path)
        mock_makedirs.assert_not_called()

    @patch('os.getenv')
    @patch('os.path.exists')
    @patch('os.makedirs')
    def test_get_app_data_path_without_appdata_dir_not_exists(self, mock_makedirs, mock_exists, mock_getenv):
        # Setup mocks
        mock_getenv.return_value = None
        mock_exists.return_value = False

        # Call function
        result = config_manager.get_app_data_path()

        # Assertions
        expected_path = os.path.join('.', 'jBahrsClipGenerator')
        self.assertEqual(result, expected_path)
        mock_getenv.assert_called_once_with('APPDATA')
        mock_exists.assert_called_once_with(expected_path)
        mock_makedirs.assert_called_once_with(expected_path)

    @patch('os.getenv')
    @patch('os.path.exists')
    @patch('os.makedirs')
    def test_get_app_data_path_without_appdata_empty_string(self, mock_makedirs, mock_exists, mock_getenv):
        # Setup mocks
        mock_getenv.return_value = ''
        mock_exists.return_value = False

        # Call function
        result = config_manager.get_app_data_path()

        # Assertions
        expected_path = os.path.join('.', 'jBahrsClipGenerator')
        self.assertEqual(result, expected_path)
        mock_getenv.assert_called_once_with('APPDATA')
        mock_exists.assert_called_once_with(expected_path)
        mock_makedirs.assert_called_once_with(expected_path)

if __name__ == '__main__':
    unittest.main()
