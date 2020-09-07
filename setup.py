import os

from setuptools import setup, find_packages
from setuptools.command.install import install
from setuptools.command.develop import develop
from setuptools.command.egg_info import egg_info

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'README.md')) as f:
    README = f.read()
with open(os.path.join(here, 'CHANGES.txt')) as f:
    CHANGES = f.read()

requires = [
    'plaster_pastedeploy',
    'pyramid',
    'pyramid_jinja2',
    'pyramid_debugtoolbar',
    'waitress',
    'alembic',
    'pyramid_retry',
    'pyramid_tm',
    'SQLAlchemy',
    'transaction',
    'zope.sqlalchemy',
    'deform',
    'paginate',
    'plotly',
    'bcrypt',
    'marshmallow-sqlalchemy',
    'metar',
    'requests',
    'mysqlclient',
    'celery',
    'tzwhere',
    'redis',
    'tensorflow',
    'keras',
    'tensorflow-docs',
    'astral'
]

import subprocess

class NPMInstall(install):
    def run(self):
        subprocess.call(['npm','install'],cwd='cycling_data')
        install.run(self)

class NPMDevelop(develop):
    def run(self):
        subprocess.call(['npm','install'],cwd='cycling_data')
        develop.run(self)

class NPMEggInfo(egg_info):
    def run(self):
        subprocess.call(['npm','install'],cwd='cycling_data')
        egg_info.run(self)

tests_require = [
    'WebTest >= 1.3.1',  # py3 compat
    'pytest >= 3.7.4',
    'pytest-cov',
]

def compile_extension_functions():
    """Used the subprocess module to compile/install the C software."""
    src_path = '.'

    # compile the software
    cmd = "cmake ."
    subprocess.check_call(cmd, cwd=src_path, shell=True)

    # install the software (into the virtualenv bin dir if present)
    subprocess.check_call('make', cwd=src_path, shell=True)

class ExtensionFunctionsInstall(NPMInstall):
    """Custom handler for the 'install' command."""
    def run(self):
        compile_and_install_software()
        super().run()

setup(
    name='cycling_data',
    version='0.0',
    description='cycling_data',
    long_description=README + '\n\n' + CHANGES,
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Pyramid',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
    ],
    cmdclass={
        'install':ExtensionFunctionsInstall,
        'develop': NPMDevelop,
        'egg_info': NPMEggInfo,
    },
    author='',
    author_email='',
    url='',
    keywords='web pyramid pylons',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    extras_require={
        'testing': tests_require,
    },
    install_requires=requires,
    entry_points={
        'paste.app_factory': [
            'main = cycling_data:main',
        ],
        'console_scripts': [
            'initialize_cycling_data_db=cycling_data.scripts.initialize_db:main',
            'regression_test=cycling_data.scripts.regression_test:main',
            'import_from_old_db=cycling_data.scripts.import_from_old_db:main',
            'plot_speed_deltas=cycling_data.scripts.plot_speed_deltas:main',
            'plot_odometer_deltas=cycling_data.scripts.plot_odometer_deltas:main',
            'docker_secrets_to_ini=cycling_data.scripts.docker_secrets_to_ini:main'
        ],
    },
    package_data = {
        'cycling_data':['lib/*']
    }
)
