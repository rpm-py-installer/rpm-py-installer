import pkg_resources
import setuptools


def get_rpm_distribution():
    for dist in ['rpm', 'rpm-python']:
        try:
            pkg_resources.get_distribution(dist)
        except pkg_resources.DistributionNotFound:
            continue
        else:
            return dist
    return 'rpm-py-installer'


install_requires = [
    'numpy',
]

install_requires.append(get_rpm_distribution())

setuptools.setup(
    name='sample',
    version='1.0.0',
    install_requires=install_requires,
)
