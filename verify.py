"""离线回归检查：模拟模型响应，并运行真实命令行流程。"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from video_assistant_app.services.code_request import CODE_MODEL, ManualCodeRequester
from video_assistant_app.services.planning import DeepSeekPlanner
from video_assistant_app.services.workflow import VideoService
from video_assistant_app.storage.projects import ProjectStore

ROOT = Path(__file__).resolve().parent


def response(text='测试制作方案', finish='stop'):
    return SimpleNamespace(choices=[SimpleNamespace(finish_reason=finish, message=SimpleNamespace(content=text))])


def isolated_copy(destination):
    """复制真实入口和模块，在临时目录运行，不写交付目录。"""
    shutil.copy2(ROOT / 'video_assistant.py', destination / 'video_assistant.py')
    shutil.copytree(ROOT / 'video_assistant_app', destination / 'video_assistant_app', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    return destination / 'video_assistant.py'


class VideoAssistantTests(unittest.TestCase):
    def test_deepseek_request_settings(self):
        client = MagicMock()
        client.chat.completions.create.return_value = response()
        factory = MagicMock()
        factory.return_value.__enter__.return_value = client
        with patch('video_assistant_app.services.planning.load_dotenv'), patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'offline-placeholder', 'DEEPSEEK_MODEL': 'deepseek-flash'}):
            self.assertEqual(DeepSeekPlanner(ROOT, factory).plan('做一个20秒动画'), '测试制作方案')
        self.assertEqual(factory.call_args.kwargs['base_url'], 'https://api.deepseek.com')
        request = client.chat.completions.create.call_args.kwargs
        self.assertEqual(request['model'], 'deepseek-flash')
        self.assertEqual(request['messages'][1]['content'], '做一个20秒动画')
        self.assertEqual(request['extra_body'], {'thinking': {'type': 'disabled'}})

    def test_no_key_stops_before_request(self):
        factory = MagicMock()
        with patch('video_assistant_app.services.planning.load_dotenv'), patch.dict(os.environ, {'DEEPSEEK_API_KEY': ''}):
            with self.assertRaises(ValueError):
                DeepSeekPlanner(ROOT, factory).plan('做视频')
        factory.assert_not_called()

    def test_empty_and_truncated_plans_are_rejected(self):
        for result in [response(''), response('部分方案', 'length'), SimpleNamespace(choices=[])]:
            client = MagicMock()
            client.chat.completions.create.return_value = result
            factory = MagicMock()
            factory.return_value.__enter__.return_value = client
            with patch('video_assistant_app.services.planning.load_dotenv'), patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'offline-placeholder'}):
                with self.assertRaises(ValueError):
                    DeepSeekPlanner(ROOT, factory).plan('做视频')

    def test_manual_request_has_no_code(self):
        task = ManualCodeRequester().request('原始需求', '制作方案')
        self.assertEqual(task['status'], 'waiting_for_code')
        self.assertEqual(task['code_files'], [])
        self.assertEqual(task['model_config']['provider'], 'manual')
        self.assertEqual(CODE_MODEL['api_key_env'], 'OPUS_API_KEY')
        self.assertIn('原始需求', task['prompt'])
        self.assertIn('制作方案', task['prompt'])

    def test_unimplemented_adapter_fails_explicitly(self):
        with self.assertRaises(NotImplementedError):
            ManualCodeRequester({'provider': 'official_api'}).request('需求', '方案')

    def test_save_import_and_version_retention(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            store = ProjectStore(root / 'projects')
            task = ManualCodeRequester().request('动画', '方案')
            first = store.create('动画', '方案', task, 'offline')
            second = store.create('动画', '方案', task, 'offline')
            self.assertNotEqual(first, second)
            state = json.loads((first / 'project.json').read_text(encoding='utf-8'))
            self.assertEqual(state['planning_mode'], 'offline')
            self.assertEqual(state['status'], 'waiting_for_code')
            self.assertEqual((first / 'plan.md').read_text(encoding='utf-8'), '方案')
            self.assertEqual((first / 'code_request.md').read_text(encoding='utf-8'), task['prompt'])
            source = root / 'scene.py'
            source.write_text("raise RuntimeError('This must not execute')\n", encoding='utf-8')
            version_one = store.import_code(first, source)
            version_two = store.import_code(first, source)
            self.assertNotEqual(version_one, version_two)
            self.assertEqual(version_two.read_text(encoding='utf-8'), source.read_text(encoding='utf-8'))
            state = json.loads((first / 'project.json').read_text(encoding='utf-8'))
            self.assertEqual(state['status'], 'code_imported')
            self.assertEqual(len(state['code_files']), 2)
            self.assertNotIn('offline-placeholder', json.dumps(state))

    def test_outside_project_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            store = ProjectStore(Path(temp) / 'projects')
            with self.assertRaises(ValueError):
                store.import_code(Path(temp) / 'outside', Path(temp) / 'code.py')

    def test_bad_file_type_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            store = ProjectStore(root / 'projects')
            project = store.create('需求', '方案', ManualCodeRequester().request('需求', '方案'), 'offline')
            source = root / 'image.png'
            source.write_bytes(b'not-code')
            with self.assertRaises(ValueError):
                store.import_code(project, source)

    def test_service_pushes_events_and_offline_skips_model(self):
        with tempfile.TemporaryDirectory() as temp:
            planner = MagicMock()
            planner.plan.return_value = '模型方案'
            service = VideoService(planner, ManualCodeRequester(), ProjectStore(Path(temp) / 'projects'))
            events = []
            service.subscribe(lambda name, data: events.append((name, data)))
            offline_project = service.create_project('离线动画', offline=True)
            planner.plan.assert_not_called()
            self.assertEqual(events[0][0], 'project_created')
            self.assertEqual(events[0][1]['project_dir'], offline_project)
            self.assertIn('尚未经过模型策划', events[0][1]['plan'])
            online_project = service.create_project('在线动画')
            planner.plan.assert_called_once_with('在线动画')
            self.assertEqual(events[1][1]['project_dir'], online_project)
            source = Path(temp) / 'scene.py'
            source.write_text('pass\n', encoding='utf-8')
            imported = service.import_code(offline_project, source)
            self.assertEqual(events[2], ('code_imported', {'target': imported}))

    def test_actual_offline_command_without_model(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            script = isolated_copy(root)
            environment = {**os.environ, 'DEEPSEEK_API_KEY': '', 'OPENAI_API_KEY': '', 'OPUS_API_KEY': ''}
            result = subprocess.run([sys.executable, str(script), '--offline'], input='用HTML制作20秒排序动画\n', text=True, capture_output=True, env=environment, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            projects = list((root / 'projects').glob('project-*'))
            self.assertEqual(len(projects), 1)
            state = json.loads((projects[0] / 'project.json').read_text(encoding='utf-8'))
            self.assertEqual(state['planning_mode'], 'offline')
            self.assertEqual(state['status'], 'waiting_for_code')
            self.assertIn('尚未经过模型策划', (projects[0] / 'plan.md').read_text(encoding='utf-8'))

    def test_actual_import_command_without_model(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            script = isolated_copy(root)
            environment = {**os.environ, 'DEEPSEEK_API_KEY': '', 'OPENAI_API_KEY': '', 'OPUS_API_KEY': ''}
            created = subprocess.run([sys.executable, str(script), '--offline'], input='排序动画\n', text=True, capture_output=True, env=environment, timeout=10)
            self.assertEqual(created.returncode, 0, created.stderr)
            project = next((root / 'projects').glob('project-*'))
            source = root / 'scene.py'
            source.write_text("raise RuntimeError('导入时不得执行')\n", encoding='utf-8')
            result = subprocess.run([sys.executable, str(script), '--project', str(project), '--import-code', str(source)], text=True, capture_output=True, env=environment, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            state = json.loads((project / 'project.json').read_text(encoding='utf-8'))
            self.assertEqual(state['status'], 'code_imported')
            self.assertEqual((project / state['code_files'][0]).read_text(encoding='utf-8'), source.read_text(encoding='utf-8'))
            self.assertIn('尚未运行或渲染', result.stdout)

    def test_cli_rejects_unpaired_arguments_and_empty_input(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            script = isolated_copy(root)
            environment = {**os.environ, 'DEEPSEEK_API_KEY': '', 'OPENAI_API_KEY': '', 'OPUS_API_KEY': ''}
            cases = [(['--project', 'missing'], '--import-code'),
                     (['--import-code', 'missing.py'], '--project'),
                     (['--offline'], '视频需求不能为空')]
            for arguments, expected in cases:
                with self.subTest(arguments=arguments):
                    result = subprocess.run([sys.executable, str(script), *arguments], input='  \n', text=True, capture_output=True, env=environment, timeout=10)
                    self.assertEqual(result.returncode, 1, result.stderr)
                    self.assertIn(expected, result.stdout)
                    self.assertFalse((root / 'projects').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
