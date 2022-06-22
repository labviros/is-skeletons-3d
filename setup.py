from setuptools import setup, find_packages

setup(
    name='is_skeletons_3d',
    version='0.0.1',
    description='',
    url='http://github.com/labviros/is-skeletons-3d',
    author='labviros',
    license='MIT',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    entry_points={
        'console_scripts': ['is-skeletons-3d=is_skeletons_3d.service:main',],
    },
    zip_safe=False,
    install_requires=[
        'is-wire==1.2.0',
        'is-msgs==1.1.10',
        'opencv-python==4.1.0.*',
        'numpy==1.22.0',
        'matplotlib==2.1.1',
        'opencensus-ext-zipkin==0.2.1',
        'python-dateutil==2.8.0',
    ],
)