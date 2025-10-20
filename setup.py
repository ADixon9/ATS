from setuptools import setup, find_packages

setup(
    name='ats',
    version='0.1.0',
    description='AeroForce Test System Software Suite',
    author='Andrew Dixon',
    author_email='andrew.dixon@udri.udayton.edu',
    packages=find_packages(),
    install_requires=[
        'contourpy==1.3.2',
        'cycler==0.12.1',
        'fonttools==4.58.0',
        'kiwisolver==1.4.8',
        'matplotlib==3.10.3',
        'numpy==2.2.5',
        'packaging==25.0',
        'pandas==2.2.3',
        'pigpio==1.78',
        'pillow==11.2.1',
        'pyparsing==3.2.3',
        'python-dateutil==2.9.0.post0',
        'pytz==2025.2',
        'simple-pid==2.0.1',
        'six==1.17.0',
        'smbus3==0.5.5',
        'tzdata==2025.2',
        'scipy==1.16.2',
        'scikit-learn==1.7.2'
    ],
    entry_points={
        'console_scripts':[
            'ats = ats_suite.gui:main',
            'ATS = ats_suite.gui:main'
        ]
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'Operating System :: POSIX :: Linux',
        'License :: OSI Approved, MIT License'
    ]
)
