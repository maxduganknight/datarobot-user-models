"""
Copyright 2021 DataRobot, Inc. and its affiliates.
All rights reserved.
This is proprietary source code of DataRobot, Inc. and its affiliates.
Released under the terms of DataRobot Tool and Utility Agreement.
"""
import argparse
import contextlib
import os
import sys
import tempfile
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest.mock import patch

import pytest

from datarobot_drum.drum.args_parser import CMRunnerArgsRegistry
from datarobot_drum.drum.enum import ArgumentsOptions, ArgumentOptionsEnvVars
from datarobot_drum.resource.utils import _exec_shell_cmd
from datarobot_drum.drum.utils.drum_utils import unset_drum_supported_env_vars


def set_sys_argv(cmd_line_args):
    # This is required because the sys.argv is manipulated by the 'CMRunnerArgsRegistry'
    cmd_line_args = cmd_line_args.copy()
    cmd_line_args.insert(0, sys.argv[0])
    sys.argv = cmd_line_args


def execute_arg_parser(success=True):
    arg_parser = CMRunnerArgsRegistry.get_arg_parser()
    CMRunnerArgsRegistry.extend_sys_argv_with_env_vars()
    if success:
        options = arg_parser.parse_args()
        CMRunnerArgsRegistry.verify_options(options)
    else:
        with pytest.raises(SystemExit):
            options = arg_parser.parse_args()
            CMRunnerArgsRegistry.verify_options(options)


class TestDrumHelp:
    @pytest.mark.parametrize(
        "cmd",
        [
            "{}".format(ArgumentsOptions.MAIN_COMMAND),
            "{} --help".format(ArgumentsOptions.MAIN_COMMAND),
        ],
    )
    def test_drum_help(self, cmd):
        _, stdo, _ = _exec_shell_cmd(
            cmd,
            "Failed in {} command line! {}".format(ArgumentsOptions.MAIN_COMMAND, cmd),
            assert_if_fail=False,
        )
        assert "usage: drum" in str(stdo)

    def test_drum_bad_subparser(self):
        cmd = "{} some_command".format(ArgumentsOptions.MAIN_COMMAND)
        _, _, stde = _exec_shell_cmd(
            cmd,
            "Failed in {} command line! {}".format(ArgumentsOptions.MAIN_COMMAND, cmd),
            assert_if_fail=False,
        )
        assert "argument subparser_name: invalid choice: 'some_command'" in str(stde)


class TestMulticlassLabelsParser(object):
    @pytest.fixture
    def parser(self):
        test_parser = argparse.ArgumentParser()
        subparsers = test_parser.add_subparsers(dest="command")
        label_parser = subparsers.add_parser("dummy")
        CMRunnerArgsRegistry._reg_arg_multiclass_labels(label_parser)
        return test_parser

    @pytest.fixture
    def class_labels(self):
        return list("ABC")

    @pytest.fixture
    def unordered_class_labels(self):
        return list("BAC")

    @pytest.fixture
    def class_labels_with_spaces(self):
        return ["Label {}".format(i) for i in range(4)]

    @pytest.mark.parametrize(
        "valid_labels", ["class_labels", "unordered_class_labels", "class_labels_with_spaces"]
    )
    @pytest.mark.parametrize("as_file", [True, False])
    def test_valid_class_labels(self, request, valid_labels, as_file, parser):
        valid_labels = request.getfixturevalue(valid_labels)
        with NamedTemporaryFile() as f:
            if as_file:
                f.write("\n".join(valid_labels).encode("utf-8"))
                f.flush()
                args = "dummy --class-labels-file {}".format(f.name).split()
            else:
                args = ["dummy", "--class-labels", *valid_labels]
            options = parser.parse_args(args)

        assert options.class_labels == valid_labels

    @pytest.mark.parametrize("as_file", [True, False])
    def test_too_few_labels(self, as_file, parser):
        labels = list("A")
        with NamedTemporaryFile() as f:
            if as_file:
                f.write("\n".join(labels).encode("utf-8"))
                f.flush()
                args = "dummy --class-labels-file {}".format(f.name).split()
            else:
                args = ["dummy", "--class-labels", *labels]

            with pytest.raises(argparse.ArgumentTypeError, match="at least 2"):
                parser.parse_args(args)


class TestPosNegLabelsParser(object):
    @pytest.fixture
    def parser(self):
        test_parser = argparse.ArgumentParser()
        subparsers = test_parser.add_subparsers(dest="command")
        label_parser = subparsers.add_parser("dummy")
        CMRunnerArgsRegistry._reg_arg_pos_neg_labels(label_parser)
        return test_parser

    @pytest.fixture
    def numeric_class_labels(self):
        return [1.0, 0.0]

    @pytest.fixture
    def bool_class_labels(self):
        return [True, False]

    @pytest.fixture
    def str_class_labels(self):
        return ["Yes", "No"]

    @pytest.mark.parametrize(
        "valid_labels", ["numeric_class_labels", "bool_class_labels", "str_class_labels"]
    )
    def test_valid_class_labels(self, request, valid_labels, parser):
        valid_labels = request.getfixturevalue(valid_labels)
        args = "dummy --positive-class-label {} --negative-class-label {}".format(
            valid_labels[0], valid_labels[1]
        ).split()
        with patch.object(sys, "argv", args):
            options = parser.parse_args(args)

        actual_labels = [options.positive_class_label, options.negative_class_label]
        assert all(isinstance(label, str) for label in actual_labels)
        assert actual_labels == [str(label) for label in valid_labels]


class TestStrictValidationParser(object):
    @pytest.fixture
    def parser(self):
        test_parser = argparse.ArgumentParser()
        subparsers = test_parser.add_subparsers(dest="command")
        label_parser = subparsers.add_parser("dummy")
        CMRunnerArgsRegistry._reg_arg_strict_validation(label_parser)
        return test_parser

    def test_disable_strict_validation(self, parser):
        args = "dummy --disable-strict-validation".split()
        with patch.object(sys, "argv", args):
            options = parser.parse_args(args)

        assert options.disable_strict_validation

    def test_enable_strict_validation(self, parser):
        # Test the strict validation is enabled by default
        args = "dummy".split()
        with patch.object(sys, "argv", args):
            options = parser.parse_args(args)

        assert not options.disable_strict_validation


class TestFitMetricsReportParser(object):
    @pytest.fixture
    def parser(self):
        test_parser = argparse.ArgumentParser()
        subparsers = test_parser.add_subparsers(dest="command")
        label_parser = subparsers.add_parser("dummy")
        CMRunnerArgsRegistry._reg_arg_report_fit_predict_metadata(label_parser)
        return test_parser

    def test_enable_metadata_report(self, parser):
        args = "dummy --enable-fit-metadata".split()
        with patch.object(sys, "argv", args):
            options = parser.parse_args(args)
        assert options.enable_fit_metadata

    def test_disable_metadata_report(self, parser):
        args = "dummy".split()
        with patch.object(sys, "argv", args):
            options = parser.parse_args(args)
        assert not options.enable_fit_metadata


class TestBooleanArgumentOptions:
    def test_boolean_argument_options_passed_through_env_var(self):
        args = f"{ArgumentsOptions.MAIN_COMMAND} server  --with-error-server --skip-predict".split()
        with patch.object(sys, "argv", args):
            unset_drum_supported_env_vars()
            CMRunnerArgsRegistry.get_arg_parser()
            os.environ[ArgumentOptionsEnvVars.PRODUCTION] = "True"
            os.environ[ArgumentOptionsEnvVars.MONITOR] = "False"
            os.environ[ArgumentOptionsEnvVars.WITH_ERROR_SERVER] = "1"
            os.environ[ArgumentOptionsEnvVars.SKIP_PREDICT] = "False"
            os.environ[ArgumentOptionsEnvVars.ALLOW_DR_API_ACCESS_FOR_ALL_CUSTOM_MODELS] = "True"
            CMRunnerArgsRegistry.extend_sys_argv_with_env_vars()
            assert ArgumentsOptions.PRODUCTION in sys.argv
            assert ArgumentsOptions.MONITOR not in sys.argv
            assert ArgumentsOptions.WITH_ERROR_SERVER in sys.argv
            assert ArgumentsOptions.SKIP_PREDICT in sys.argv
            assert sys.argv.count(ArgumentsOptions.WITH_ERROR_SERVER) == 1
            assert sys.argv.count(ArgumentsOptions.SKIP_PREDICT) == 1
            assert ArgumentsOptions.ALLOW_DR_API_ACCESS_FOR_ALL_CUSTOM_MODELS in sys.argv
            unset_drum_supported_env_vars()


class TestMonitorArgs:
    @pytest.fixture(scope="session")
    def tmp_dir_with_dataset(self):
        with tempfile.TemporaryDirectory() as tmpdirname:
            input_filepath = Path(tmpdirname) / "input.csv"
            open(input_filepath, "wb").write(b"a,b,c\n1,2,3")
            yield str(input_filepath)

    @pytest.fixture
    def minimal_score_cmd_args(self, tmp_dir_with_dataset):
        return ["score", "--code-dir", "/tmp", "--input", tmp_dir_with_dataset]

    @pytest.fixture
    def binary_score_cmd_args(self, minimal_score_cmd_args):
        minimal_score_cmd_args.extend(["--target-type", "binary"])
        return minimal_score_cmd_args

    @pytest.fixture
    def unstructured_score_cmd_args(self, minimal_score_cmd_args):
        minimal_score_cmd_args.extend(["--target-type", "unstructured"])
        return minimal_score_cmd_args

    @pytest.fixture
    def monitor_cmd_args(self):
        return [
            "--monitor",
            "--deployment-id",
            "123",
            "--model-id",
            "456",
            "--monitor-settings",
            "aaa;bbb",
        ]

    @pytest.fixture
    def monitor_embedded_cmd_args_without_monitor_settings(self):
        return [
            "--monitor-embedded",
            "--deployment-id",
            "123",
            "--model-id",
            "456",
            "--webserver",
            "http://aaa.bbb.ccc",
            "--api-token",
            "zzz",
        ]

    @pytest.fixture
    def monitor_env_vars(self):
        os.environ[ArgumentOptionsEnvVars.MONITOR] = "True"
        os.environ["DEPLOYMENT_ID"] = "e123"
        os.environ["MODEL_ID"] = "e456"
        os.environ["MONITOR_SETTINGS"] = "e;aaa;bbb"
        yield
        os.environ.pop(ArgumentOptionsEnvVars.MONITOR)
        os.environ.pop("DEPLOYMENT_ID")
        os.environ.pop("MODEL_ID")
        os.environ.pop("MONITOR_SETTINGS")

    @pytest.fixture
    def monitor_embedded_env_vars(self):
        os.environ[ArgumentOptionsEnvVars.MONITOR_EMBEDDED] = "true"
        os.environ["DEPLOYMENT_ID"] = "e123"
        os.environ["MODEL_ID"] = "e456"
        os.environ["EXTERNAL_WEB_SERVER_URL"] = "e-http://aaa.bbb.ccc"
        os.environ["API_TOKEN"] = "e-zzz"
        yield
        os.environ.pop(ArgumentOptionsEnvVars.MONITOR_EMBEDDED)
        os.environ.pop("DEPLOYMENT_ID")
        os.environ.pop("MODEL_ID")
        os.environ.pop("EXTERNAL_WEB_SERVER_URL")
        os.environ.pop("API_TOKEN")

    def test_binary_monitor_from_cmd_line_args_success(
        self, binary_score_cmd_args, monitor_cmd_args
    ):
        binary_score_cmd_args.extend(monitor_cmd_args)
        set_sys_argv(binary_score_cmd_args)
        execute_arg_parser()

    @pytest.mark.usefixtures("monitor_env_vars")
    def test_binary_monitor_from_env_vars_success(self, binary_score_cmd_args):
        set_sys_argv(binary_score_cmd_args)
        execute_arg_parser()

    @pytest.mark.usefixtures("monitor_env_vars")
    def test_binary_monitor_from_cmd_line_and_env_vars_success(
        self, binary_score_cmd_args, monitor_cmd_args
    ):
        # pop the last 2 elements in order to take them from the environment
        monitor_cmd_args = monitor_cmd_args[0:-2]
        binary_score_cmd_args.extend(monitor_cmd_args)
        set_sys_argv(binary_score_cmd_args)
        execute_arg_parser()

    def test_binary_monitor_embedded_cmd_args_failure(
        self, binary_score_cmd_args, monitor_embedded_cmd_args_without_monitor_settings
    ):
        binary_score_cmd_args.extend(monitor_embedded_cmd_args_without_monitor_settings)
        set_sys_argv(binary_score_cmd_args)
        execute_arg_parser(success=False)

    @pytest.mark.usefixtures("monitor_embedded_env_vars")
    def test_binary_monitor_embedded_from_env_vars_failure(self, binary_score_cmd_args):
        set_sys_argv(binary_score_cmd_args)
        execute_arg_parser(success=False)

    def test_binary_mutually_exclusive_args_failure(
        self,
        binary_score_cmd_args,
        monitor_cmd_args,
        monitor_embedded_cmd_args_without_monitor_settings,
    ):
        args = binary_score_cmd_args
        args.extend(monitor_cmd_args)
        args.extend(monitor_embedded_cmd_args_without_monitor_settings)
        set_sys_argv(args)
        execute_arg_parser(success=False)

    @pytest.mark.parametrize(
        "monitor_settings", [(), ("--monitor-settings", "aaa;bbb")],
    )
    def test_unstructured_monitor_embedded_from_cmd_line_args_success(
        self,
        unstructured_score_cmd_args,
        monitor_embedded_cmd_args_without_monitor_settings,
        monitor_settings,
    ):
        unstructured_score_cmd_args.extend(monitor_embedded_cmd_args_without_monitor_settings)
        unstructured_score_cmd_args.extend(monitor_settings)
        set_sys_argv(unstructured_score_cmd_args)
        execute_arg_parser()

    @pytest.mark.parametrize(
        "env_var_key, env_var_value", [(None, None), ("MONITOR_SETTINGS", "aaa;bbb")],
    )
    @pytest.mark.usefixtures("monitor_embedded_env_vars")
    def test_unstructured_monitor_from_env_vars_success(
        self, unstructured_score_cmd_args, env_var_key, env_var_value
    ):
        if env_var_key:
            os.environ[env_var_key] = env_var_value
        set_sys_argv(unstructured_score_cmd_args)
        execute_arg_parser()
        if env_var_key:
            os.environ.pop(env_var_key)

    @pytest.mark.usefixtures("monitor_embedded_env_vars")
    def test_unstructured_monitor_from_cmd_line_and_env_vars_success(
        self, unstructured_score_cmd_args, monitor_embedded_cmd_args_without_monitor_settings
    ):
        # pop the last 2 elements in order to take them from the environment
        monitor_embedded_cmd_args_without_monitor_settings = monitor_embedded_cmd_args_without_monitor_settings[
            0:-2
        ]
        unstructured_score_cmd_args.extend(monitor_embedded_cmd_args_without_monitor_settings)
        set_sys_argv(unstructured_score_cmd_args)
        execute_arg_parser()

    def test_unstructured_monitor_cmd_args_failure(
        self, unstructured_score_cmd_args, monitor_cmd_args
    ):
        unstructured_score_cmd_args.extend(monitor_cmd_args)
        set_sys_argv(unstructured_score_cmd_args)
        execute_arg_parser(success=False)

    @pytest.mark.usefixtures("monitor_env_vars")
    def test_unstructured_monitor_from_env_vars_failure(self, unstructured_score_cmd_args):
        set_sys_argv(unstructured_score_cmd_args)
        execute_arg_parser(success=False)

    def test_unstructured_mutually_exclusive_args_failure(
        self,
        unstructured_score_cmd_args,
        monitor_cmd_args,
        monitor_embedded_cmd_args_without_monitor_settings,
    ):
        args = unstructured_score_cmd_args
        args.extend(monitor_cmd_args)
        args.extend(monitor_embedded_cmd_args_without_monitor_settings)
        set_sys_argv(args)
        execute_arg_parser(success=False)


class TestDrApiAccess:
    @pytest.fixture(
        scope="class",
        params=[
            ["score", "--target-type", "binary", "--code-dir", "/tmp", "--input", __file__],
            [
                "server",
                "--target-type",
                "unstructured",
                "--code-dir",
                "/tmp",
                "--address",
                "127.0.1.1",
            ],
        ],
    )
    def _cli_args(self, request):
        yield request.param

    @contextlib.contextmanager
    def _dr_api_access_env_vars(self, enabled=True, skipped_env_var=None):
        args = {
            ArgumentOptionsEnvVars.ALLOW_DR_API_ACCESS_FOR_ALL_CUSTOM_MODELS: str(enabled),
            "EXTERNAL_WEB_SERVER_URL": "http://aaa.bbb.ccc",
            "API_TOKEN": "zzz123",
        }
        for env_var, value in args.items():
            if env_var != skipped_env_var:
                os.environ[env_var] = value

        yield

        for env_var in args:
            os.environ.pop(env_var, None)

    def test_dr_api_access_from_env_var_success(self, _cli_args):
        with self._dr_api_access_env_vars():
            set_sys_argv(_cli_args)
            execute_arg_parser()

    @pytest.mark.parametrize("missing_mandatory_env_var", ["EXTERNAL_WEB_SERVER_URL", "API_TOKEN"])
    def test_dr_api_access_from_env_var_missing_var(self, _cli_args, missing_mandatory_env_var):
        with self._dr_api_access_env_vars(enabled=True, skipped_env_var=missing_mandatory_env_var):
            set_sys_argv(_cli_args)
            with pytest.raises(SystemExit) as ex:
                execute_arg_parser()

    @pytest.mark.parametrize(
        "missing_mandatory_env_var", [None, "EXTERNAL_WEB_SERVER_URL", "API_TOKEN"]
    )
    def test_dr_api_access_inactive_success(self, _cli_args, missing_mandatory_env_var):
        with self._dr_api_access_env_vars(enabled=False, skipped_env_var=missing_mandatory_env_var):
            set_sys_argv(_cli_args)
            execute_arg_parser()
