import pytest
from trio_websocket import serve_websocket

from tests.helpers import get_fake_input, server_handler
from ws.commands.session import main
from ws.main import cli
from ws.utils.command import Command


def test_should_print_error_when_url_is_not_given(runner):
    result = runner.invoke(cli, ['session'])

    assert result.exit_code == 2
    assert "Missing argument 'URL'" in result.output


def test_should_print_error_when_filename_is_not_a_file(tmp_path, runner):
    result = runner.invoke(cli, ['session', ':1234', '-f', f'{tmp_path}'])

    assert result.exit_code == 2
    assert 'is a directory' in result.output


async def test_should_exit_program_when_user_makes_a_ctrl_d(capsys, mocker, nursery):
    # Ctrl+D raises an EOFError, so to simulate it, we will raise this error on console.input method
    mocker.patch('ws.console.console.input', side_effect=EOFError)
    await nursery.start(serve_websocket, server_handler, 'localhost', 1234, None)
    await main('ws://localhost:1234')
    output = capsys.readouterr().out

    assert 'Welcome to the interactive websocket session! 🌟\n' in output
    assert 'For more information about commands, type the help command.\n' in output
    assert 'When you see <> around a word, it means this argument is optional.\n' in output
    assert 'To know more about a particular command type help <command>.\n' in output
    assert 'To close the session, you can type Ctrl+D or the quit command.\n' in output
    assert 'Bye! 👋\n' in output


async def test_should_print_error_message_when_an_unknown_command_is_given_as_input(capsys, mocker, nursery):
    mocker.patch('ws.console.console.input', get_fake_input('foo'))
    await nursery.start(serve_websocket, server_handler, 'localhost', 1234, None)
    await main('ws://localhost:1234')
    output = capsys.readouterr().out

    assert 'Unknown command foo, available commands are:\n' in output
    for command in Command:
        assert f'• {command.value}\n' in output
    assert 'Bye!' in output


async def test_should_continue_prompting_user_if_input_is_empty(capsys, mocker, nursery):
    count = 0

    def fake_input(_prompt):
        nonlocal count
        if count == 0:
            count += 1
            return ''
        elif count == 1:
            count += 1
            return '  '
        else:
            return 'quit'

    mocker.patch('ws.console.console.input', fake_input)
    await nursery.start(serve_websocket, server_handler, 'localhost', 1234, None)
    await main('ws://localhost:1234')
    output = capsys.readouterr().out

    assert 'Bye! 👋\n' in output


@pytest.mark.parametrize('filename', ['file.txt', 'file.html', 'file.svg'])
@pytest.mark.usefixtures('reset_console')
async def test_should_print_input_and_save_it_in_a_file(capsys, tmp_path, mocker, nursery, filename):
    file_path = tmp_path / filename
    mocker.patch('ws.console.console.input', get_fake_input('help'))
    await nursery.start(serve_websocket, server_handler, 'localhost', 1234, None)
    await main('ws://localhost:1234', filename=f'{file_path}')
    terminal_output = capsys.readouterr().out

    first_sentence = 'Welcome to the interactive websocket session! 🌟\n'
    second_sentence = 'The session program lets you interact with a websocket endpoint'
    last_sentence = 'Bye! 👋\n'
    assert first_sentence in terminal_output
    assert second_sentence in terminal_output
    assert last_sentence in terminal_output

    file_output = file_path.read_text()

    first_sentence = first_sentence.replace('\n', '')
    last_sentence = last_sentence.replace('\n', '')
    if file_path.suffix == '.svg':
        assert first_sentence.replace(' ', '&#160;') in file_output
        assert second_sentence.replace(' ', '&#160;') in file_output
        assert last_sentence.replace(' ', '&#160;') in file_output
    else:
        assert first_sentence in terminal_output
        assert second_sentence in terminal_output
        assert last_sentence in file_output


def test_should_check_trio_run_is_correctly_called_without_options(runner, mocker):
    run_mock = mocker.patch('trio.run')
    url = 'ws://localhost:1234'
    result = runner.invoke(cli, ['session', url])

    assert result.exit_code == 0
    run_mock.assert_called_once_with(main, url, None)


@pytest.mark.parametrize('filename_option', ['-f', '--file'])
def test_should_check_trio_run_is_correctly_called_with_options(tmp_path, runner, mocker, filename_option):
    run_mock = mocker.patch('trio.run')
    file_path = tmp_path / 'file.txt'
    result = runner.invoke(cli, ['session', ':1234', filename_option, f'{file_path}'])

    assert result.exit_code == 0
    run_mock.assert_called_once_with(main, 'ws://localhost:1234', f'{file_path}')
