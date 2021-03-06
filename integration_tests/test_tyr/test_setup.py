# encoding: utf-8

from ..docker import docker_exec
from ..utils import filter_column, python_requirements_compare
from ..test_common import skipifdev


# @skipifdev
def test_update_tyr_config_file(distributed_undeployed):
    platform, fabric = distributed_undeployed
    # create empty directory for task under test
    platform.docker_exec("mkdir -p /srv/tyr")
    value, exception, stdout, stderr = fabric.execute_forked('update_tyr_config_file')
    assert exception is None
    assert stderr == ''
    # check fabric tasks execution count
    assert stdout.count("Executing task 'update_tyr_config_file'") == 2
    # check existence of files created by the task under test
    assert platform.path_exists('/srv/tyr/settings.py')
    assert platform.path_exists('/srv/tyr/settings.wsgi')

    env = fabric.get_object('env')
    env.tyr_broker_username = 'toto'
    value, exception, stdout, stderr = fabric.execute_forked('update_tyr_config_file')
    assert exception is None
    assert stderr.count("Warning: run() received nonzero return code 1 while executing "
                        "'diff /srv/tyr/settings.py /srv/tyr/settings.py.temp'") == 2
    assert stdout.count("> CELERY_BROKER_URL = 'amqp://toto:guest@localhost:5672//'") == 2
    assert stdout.count("< CELERY_BROKER_URL = 'amqp://guest:guest@localhost:5672//'") == 2


@skipifdev
def test_setup_tyr(distributed_undeployed):
    platform, fabric = distributed_undeployed
    # create some objects used (symlinked) by the task under test
    platform.docker_exec('mkdir -p /usr/share/tyr/migrations/')
    platform.docker_exec('touch /usr/bin/manage_tyr.py')
    value, exception, stdout, stderr = fabric.execute_forked('setup_tyr')
    assert exception is None
    # check fabric tasks execution count
    assert stdout.count("Executing task 'setup_tyr'") == 2
    assert stdout.count("Executing task 'update_cities_conf'") == 2
    assert stdout.count("Executing task 'update_tyr_config_file'") == 0
    assert stdout.count("Executing task 'update_tyr_instance_conf'") == 0
    # check that user www-data exists
    assert filter_column(platform.get_data('/etc/passwd', 'host1'), 0, startswith='www-data')
    assert filter_column(platform.get_data('/etc/passwd', 'host2'), 0, startswith='www-data')
    # check existence of directories and files created by the task under test
    assert platform.path_exists('/etc/tyr.d')
    assert platform.path_exists('/srv/tyr')
    assert platform.path_exists('/var/log/tyr')
    assert platform.path_exists('/srv/ed/data/')
    assert platform.path_exists('/var/log/tyr/tyr.log')
    for instance in fabric.env.instances:
        assert platform.path_exists('/srv/ed/{}/'.format(instance))
        assert platform.path_exists('/srv/ed/{}/alembic.ini'.format(instance))
        assert platform.path_exists('/srv/ed/{}/settings.sh'.format(instance))
        assert platform.path_exists('/etc/tyr.d/{}.ini'.format(instance))
    assert platform.path_exists('/etc/init.d/tyr_worker')
    assert platform.path_exists('/srv/tyr/migrations')
    assert platform.path_exists('/srv/tyr/manage.py')
    assert platform.path_exists('/srv/tyr/cities_alembic.ini', 'host1')


@skipifdev
def test_update_tyr_confs(distributed_undeployed):
    platform, fabric = distributed_undeployed
    # create empty directories for task under test
    platform.docker_exec("mkdir -p /etc/tyr.d /srv/tyr")
    value, exception, stdout, stderr = fabric.execute_forked('update_tyr_confs')
    assert exception is None
    assert stderr == ''
    # check fabric tasks execution count
    assert stdout.count("Executing task 'update_tyr_config_file'") == 2
    assert stdout.count("Executing task 'update_tyr_instance_conf'") == 2 * len(fabric.env.instances)
    assert stdout.count("Executing task 'update_cities_conf'") == 1


@skipifdev
def test_upgrade_tyr_packages(distributed_undeployed):
    platform, fabric = distributed_undeployed
    fabric.execute('upgrade_tyr_packages')
    assert platform.get_version('python', 'host1').startswith('2.7')
    assert platform.get_version('python', 'host2').startswith('2.7')
    assert docker_exec(platform.containers['host1'], 'pip -V', return_code_only=True) == 0
    assert docker_exec(platform.containers['host2'], 'pip -V', return_code_only=True) == 0
    assert platform.get_version('navitia-tyr', 'host1')
    assert platform.get_version('navitia-tyr', 'host2')
    assert platform.get_version('navitia-common', 'host1')
    assert platform.get_version('navitia-common', 'host2')
    known_missing = ['argparse==1.2.1', 'wsgiref==0.1.2']
    for host in ('host1', 'host2'):
        assert python_requirements_compare(
            platform.docker_exec('pip freeze', host),
            platform.get_data('/usr/share/tyr/requirements.txt', host)
        ) == known_missing
    # TODO this seems redundant with setup_tyr
    assert platform.path_exists('/etc/init.d/tyr_worker')


@skipifdev
def test_setup_tyr_master(distributed_undeployed):
    platform, fabric = distributed_undeployed
    fabric.execute('setup_tyr_master')
    assert platform.path_exists('/srv/ed/', 'host1')
    assert platform.path_exists('/srv/ed/', 'host2', negate=True)
    assert platform.path_exists('/etc/init.d/tyr_beat', 'host1')
    assert platform.path_exists('/etc/init.d/tyr_beat', 'host2', negate=True)


@skipifdev
def test_upgrade_ed_packages(distributed_undeployed):
    platform, fabric = distributed_undeployed
    fabric.execute('upgrade_ed_packages')
    assert platform.get_version('navitia-ed', 'host1')
    assert platform.get_version('navitia-ed', 'host2')
    assert platform.get_version('navitia-common', 'host1')
    assert platform.get_version('navitia-common', 'host2')
    assert platform.get_version('navitia-cities', 'host1')
    assert platform.get_version('navitia-cities', 'host2')
