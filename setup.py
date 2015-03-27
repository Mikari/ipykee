from setuptools import setup

setup(
    name='ipykee',
    description='IPython module for provenance',
    author='Egor Khairullin',
    author_email='mikari@yandex-team.ru',
    packages=['ipykee'],
    package_dir={'ipykee': 'py-modules'},
    scripts=['ipykee-ssh-wrapper.sh'],
    install_requires = [
        'pyyaml',
        'nbdiff',
        'ipython',
    ],
)

