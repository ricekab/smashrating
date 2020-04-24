from setuptools import setup, find_packages

__about__ = {}
with open("smashrating/__about__.py") as fp:
    exec(fp.read(), __about__)

setup(
    name=__about__['__name__'],
    version=__about__['__version__'],
    description=__about__['__description__'],
    author='kevincyt',
    author_email='contact@kevinchiyantang.com',
    packages=find_packages(exclude=['tests']),
    url='https://github.com/ricekab/smashrating',
    license='MIT',
    install_requires=['sqlalchemy', 'psycopg2', 'requests', 'graphqlclient'],
    tests_require=['pytest'],
    python_requires='>=3.4',
    entry_points='''
        [console_scripts]
        smashcli=smashrating.cli:entry
    '''
)
