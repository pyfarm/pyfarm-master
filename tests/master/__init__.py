# No shebang line, this module is meant to be imported
#
# Copyright 2014 Oliver Palmer
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
from os.path import dirname, abspath

# load or add the utcore module
try:
    import utcore
except ImportError:
    abspath = abspath(__file__)
    tests_dir = dirname(dirname(abspath))
    if tests_dir not in sys.path:
        sys.path.insert(0, tests_dir)
    print(sys.path)
    import utcore