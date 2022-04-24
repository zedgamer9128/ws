import pytest
from trio_websocket import serve_websocket

from tests.helpers import killer, server_handler
from ws.commands.ping import main as main_ping
from ws.commands.pong import main as main_pong
from ws.main import cli

command_parametrize = pytest.mark.parametrize('command', ['ping', 'pong'])
ping_pong_parametrize = pytest.mark.parametrize('ping_pong', [main_ping, main_pong])


@command_parametrize
def test_should_print_error_when_url_argument_is_not_given(runner, command):
    result = runner.invoke(cli, [command])

    assert result.exit_code == 2
    assert "Missing argument 'URL'" in result.output


@pytest.mark.parametrize('url', ['ws:/websocket', 'https://websocket.com'])
@command_parametrize
def test_should_print_error_when_given_url_is_not_a_websocket_url(runner, url, command):
    result = runner.invoke(cli, [command, url])

    assert result.exit_code == 2
    assert f'{url} is not a valid websocket url' in result.output


@pytest.mark.parametrize('number', ['foo', '4.5'])
@command_parametrize
def test_should_print_error_when_number_is_not_an_integer(runner, number, command):
    result = runner.invoke(cli, [command, 'ws://websocket.com', '-n', number])

    assert result.exit_code == 2
    assert 'is not a valid integer' in result.output


@pytest.mark.parametrize(
    ('command', 'message'), [('ping', 'The number of pings cannot be 0'), ('pong', 'The number of pongs cannot be 0')]
)
def test_should_print_error_when_number_is_0(runner, command, message):
    result = runner.invoke(cli, [command, 'ws://websocket.com', '-n', '0'])

    assert result.exit_code == 2
    assert message in result.output


@command_parametrize
def test_should_print_error_when_interval_is_not_a_float(runner, command):
    result = runner.invoke(cli, [command, 'ws://websocket.com', '-i', 'foo'])

    assert result.exit_code == 2
    assert 'is not a valid float range' in result.output


@pytest.mark.parametrize('interval', ['-1', '0'])
@command_parametrize
def test_should_print_error_when_interval_is_not_in_the_valid_range(runner, interval, command):
    result = runner.invoke(cli, [command, 'ws://websocket.com', '-i', interval])

    assert result.exit_code == 2
    assert 'is not in the range x>0' in result.output


def test_should_print_error_when_ping_settings_are_not_correct(monkeypatch, runner):
    monkeypatch.setenv('WS_CONNECT_TIMEOUT', 'foo')
    result = runner.invoke(cli, ['ping', 'ws://websocket.com'])

    assert result.exit_code == 1
    assert 'connect_timeout' in result.output
    assert 'not a valid float' in result.output


async def test_should_make_a_one_ping_with_default_values(capsys, nursery):
    interval = 1.0
    number = 1
    url = 'ws://localhost:1234'

    await nursery.start(serve_websocket, server_handler, 'localhost', 1234, None)
    await main_ping(url, number, interval)

    assert f'PING {url} with 32 bytes of data\nsequence=1, time=' in capsys.readouterr().out


async def test_should_make_one_pong_with_default_values(capsys, nursery):
    interval = 1.0
    number = 1
    url = 'ws://localhost:1234'

    await nursery.start(serve_websocket, server_handler, 'localhost', 1234, None)
    await main_pong(url, number, interval)

    assert f'Sent unsolicited PONG of 0 bytes of data to {url}\nsequence=1, time=' in capsys.readouterr().out


@ping_pong_parametrize
async def test_should_make_five_pings_and_pongs(capsys, nursery, ping_pong):
    interval = 1.0
    number = 5
    message = b'hello'

    await nursery.start(serve_websocket, server_handler, 'localhost', 1234, None)
    await ping_pong('ws://localhost:1234', number, interval, message)
    data = capsys.readouterr().out

    assert '5 bytes of data' in data
    assert data.count('sequence') == number


@ping_pong_parametrize
async def test_should_make_infinite_number_of_pings_and_pongs(capsys, nursery, ping_pong):
    interval = 1.0
    number = -1

    await nursery.start(serve_websocket, server_handler, 'localhost', 1234, None)
    nursery.start_soon(killer, 2)
    await ping_pong('ws://localhost:1234', number, interval)
    data = capsys.readouterr().out

    assert data.count('sequence') == 2


@pytest.mark.parametrize(('command', 'ping_pong'), [('ping', main_ping), ('pong', main_pong)])
def test_should_check_trio_run_is_correctly_called_without_arguments(runner, mocker, command, ping_pong):
    run_mock = mocker.patch('trio.run')
    url = 'ws://localhost'
    result = runner.invoke(cli, [command, url])

    assert result.exit_code == 0
    run_mock.assert_called_once_with(ping_pong, url, 1, 1.0, None)


@pytest.mark.parametrize(
    ('interval_option', 'number_option', 'message_option'),
    [('-i', '-n', '-m'), ('--interval', '--number', '--message')],
)
@pytest.mark.parametrize(('command', 'ping_pong'), [('ping', main_ping), ('pong', main_pong)])
def test_should_check_trio_run_is_correctly_called_with_arguments(
    runner, mocker, interval_option, number_option, message_option, command, ping_pong
):
    run_mock = mocker.patch('trio.run')
    number = 3
    interval = 2
    message = 'hello'
    result = runner.invoke(
        cli, [command, ':8000', interval_option, interval, number_option, number, message_option, message]
    )

    assert result.exit_code == 0
    run_mock.assert_called_once_with(ping_pong, 'ws://localhost:8000', number, interval, message.encode())
