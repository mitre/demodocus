"""
Software License Agreement (Apache 2.0)

Copyright (c) 2020, The MITRE Corporation.
All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

This project was developed by The MITRE Corporation.
If this code is used in a deployment or embedded within another project,
it is requested that you send an email to opensource@mitre.org in order to
let us know where this software is being used.
"""

"""
A *User* is an instance of UserModel with a particular configuration of UserAbilitys.
- OmniUser: Can perceive and interact with everything, used for building the complete graph
"""

from demodocusfw.user import UserModel
from .ability import OmniAbility

# Abilities: Initialize these up front since we use some of them more than once.
omni_ability = OmniAbility()

# Users
OmniUser = UserModel('OmniUser', [omni_ability])
