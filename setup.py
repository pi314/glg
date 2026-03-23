from setuptools import setup


setup(
    name='glg',
    description='git lg that automatically refresh',
    author='Cychih',
    author_email='michael66230@gmail.com',
    url='https://github.com/pi314/glg',
    entry_points = {
        'console_scripts': [
            'glg=glg:__main__.main',
            ],
    },
    install_requires=['watchdog'],
    python_requires='>=3.9',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: MacOS :: MacOS X',
        'Programming Language :: Python :: 3',
        'Topic :: Utilities',
    ],
)
