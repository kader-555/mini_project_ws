from setuptools import find_packages, setup

package_name = 'nursebot_mobile_bridge'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='mouhamed-abdelkader',
    maintainer_email='medkdr2005@gmail.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'ros_bridge_node = nursebot_mobile_bridge.ros_bridge:main',
            'api_server = nursebot_mobile_bridge.api_server:main',
        ],
    },
)
