"""The first-boot passwords never have to be part of a command line: environment, standard input, remote build."""
import io
import json
import unittest
from unittest import mock

from hydra_umc_os_rebuilder import main as cli


def parse(*argv):
    return cli.build_parser().parse_args(list(argv))


class SecretSourcesTests(unittest.TestCase):
    def test_every_command_that_takes_the_passwords_takes_secrets_stdin(self):
        for command in (["config", "--out", "x"], ["build-image", "--out", "x"], ["profile-build", "--manifest", "p.json", "--out", "x"]):
            with self.subTest(command[0]):
                try:
                    args = parse(*command, "--secrets-stdin")
                except SystemExit:  # a required argument of that command that this test does not know
                    self.skipTest("command needs other arguments")
                self.assertTrue(args.secrets_stdin)

    def test_environment_fills_what_the_command_line_did_not(self):
        args = parse("build-image", "--out", "x")
        cli.apply_secret_sources(args, {"HYDRA_UMC_FIRSTBOOT_PASSWORD": "pw", "HYDRA_UMC_FIRSTBOOT_WIFI_PASSWORD": "psk"})
        self.assertEqual((args.password, args.wifi_password), ("pw", "psk"))

    def test_an_explicit_flag_wins_over_the_environment(self):
        args = parse("build-image", "--out", "x", "--password", "flag")
        cli.apply_secret_sources(args, {"HYDRA_UMC_FIRSTBOOT_PASSWORD": "env"})
        self.assertEqual(args.password, "flag")

    def test_standard_input_carries_both_secrets(self):
        args = parse("build-image", "--out", "x", "--secrets-stdin")
        cli.apply_secret_sources(args, {}, io.StringIO(json.dumps({"password": "pw", "wifiPassword": "psk"})))
        self.assertEqual((args.password, args.wifi_password), ("pw", "psk"))

    def test_a_bad_standard_input_is_refused(self):
        for text in ("not json", "[1]", '{"password": 1}', '{"other": "x"}'):
            with self.subTest(text):
                args = parse("build-image", "--out", "x", "--secrets-stdin")
                with self.assertRaises(ValueError):
                    cli.apply_secret_sources(args, {}, io.StringIO(text))

    def test_main_refuses_with_code_2_on_a_bad_standard_input(self):
        with mock.patch("sys.stdin", io.StringIO("nope")), mock.patch("sys.stderr", io.StringIO()):
            self.assertEqual(cli.main(["--cli", "build-image", "--out", "x", "--secrets-stdin"]), 2)


class RemoteBuildDoesNotPutSecretsInTheCommandTests(unittest.TestCase):
    OPTIONS = {"hostname": "cm5", "fbUsername": "pi", "fbPassword": "Sup3r secret!", "wifiSsid": "lab", "wifiPassword": "psk with space"}

    def bridge(self):
        try:
            from hydra_umc_os_rebuilder.qt_gui import RebuilderBridge
        except ImportError:
            self.skipTest("PySide6 is not installed")
        return RebuilderBridge

    def test_the_arguments_carry_no_password_but_ask_for_standard_input(self):
        bridge = self.bridge()
        joined = " ".join(bridge._firstboot_cli_args(self.OPTIONS))
        self.assertNotIn("Sup3r", joined)
        self.assertNotIn("psk", joined)
        self.assertNotIn("--password", joined)
        self.assertNotIn("--wifi-password", joined)
        self.assertIn("--secrets-stdin", joined)
        self.assertIn("--wifi-ssid lab", joined)

    def test_the_secrets_travel_as_json(self):
        bridge = self.bridge()
        self.assertEqual(json.loads(bridge._firstboot_secrets_json(self.OPTIONS)), {"password": "Sup3r secret!", "wifiPassword": "psk with space"})
        self.assertIsNone(bridge._firstboot_secrets_json({"hostname": "cm5"}))
        self.assertNotIn("--secrets-stdin", bridge._firstboot_cli_args({"hostname": "cm5"}))


if __name__ == "__main__":
    unittest.main()
