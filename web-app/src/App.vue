<!--
/*********************************************************************
* Software License Agreement (Apache 2.0)
* 
* Copyright (c) 2020, The MITRE Corporation.
* All rights reserved.
* 
* Licensed under the Apache License, Version 2.0 (the "License");
* you may not use this file except in compliance with the License.
* You may obtain a copy of the License at
* 
* https://www.apache.org/licenses/LICENSE-2.0
* 
* Unless required by applicable law or agreed to in writing, software
* distributed under the License is distributed on an "AS IS" BASIS,
* WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
* See the License for the specific language governing permissions and
* limitations under the License.
* 
* If this code is used in a deployment or embedded within another project,
* it is requested that you send an email to opensource@mitre.org in order to
* let us know where this software is being used.
*********************************************************************/
-->

<template>
  <div id="app">
    <a id="skip-link" href="#main-content">Skip to main content</a>
    <nav class="navbar fixed-top navbar-light bg-light">
      <ul class="nav nav-pills nav-fill">
        <li class="nav-item">
          <a class="nav-link">
            <router-link :to="'/dashboard'" tag="button" class="btn btn-light" data-toggle="tooltip" data-placement="bottom" title="Tooltip on bottom">
              <img src="./assets/HomeSm.png" height="30" alt="Home">
            </router-link>
          </a>
        </li>
        <li class="nav-item">
          <a class="nav-link">
            <button type="button" class="btn btn-light">
                <img src="./assets/OverviewSm.png" height="30" alt="Overview">
            </button>
          </a>
        </li>
        <li class="nav-item">
          <a class="nav-link">
            <button type="button" class="btn btn-light">
                <img src="./assets/RulesetsSm.png" height="30" alt="Rule Sets">
            </button>
          </a>
        </li>
        <li class="nav-item">
          <a class="nav-link">
            <button type="button" class="btn btn-light">
                <img src="./assets/UsersSm.png" height="30" alt="User Types">
            </button>
          </a>
        </li>
      </ul>
      <ul class="nav nav-pills nav-fill">
        <li class="nav-item">
          <a class="nav-link" @click="startTutorial">
            <button type="button" class="btn btn-light">
              <img src="./assets/help-circle.png" height="30" alt="Tutorial">
            </button>
          </a>
        </li>
        <li class="nav-item">
          <a class="nav-link">
            <button type="button" class="btn btn-light">
                <img src="./assets/ExportSm.png" height="30" alt="Export">
            </button>
          </a>
        </li>
        <li class="nav-item">
          <a class="nav-link">
            <button type="button" class="btn btn-light">
                <img src="./assets/SettingsSm.png" height="30" alt="Settings">
            </button>
          </a>
        </li>
        <li class="nav-item">
          <a class="nav-link">
            <button type="button" class="btn btn-light">
                <img src="./assets/AccountSm.png" height="30" alt="Account">
            </button>
          </a>
        </li>
      </ul>
    </nav>

    <main id="main-content" tabindex="0" role="main" class="col-md-10 col-lg-12 px-5">
      <router-view></router-view>
    </main>
  </div>
</template>

<script>
import Vue from 'vue';
import { LMap, LImageOverlay, LMarker, LPopup, LIcon, LPolygon } from 'vue2-leaflet';
import 'leaflet/dist/leaflet.css';
import introJS from 'intro.js';

Vue.component('l-map', LMap);
Vue.component('l-image-overlay', LImageOverlay);
Vue.component('l-marker', LMarker);
Vue.component('l-popup', LPopup);
Vue.component('l-icon', LIcon);
Vue.component('l-polygon', LPolygon);

export default {
  name: 'App',
  components: {
  },
  methods: {
    startTutorial() {
      console.log("Running Tutorial");
      introJS().start();
    },
  }
}
</script>

<style>

body {
    background-color: #ffffff;
}

.navbar {
    padding: 0rem 1rem !important;
}

.sm-text {
    font-size: 10px;
}

[role="main"] {
  padding-top: 133px; /* Space for fixed navbar */
}

@media (min-width: 768px) {
  [role="main"] {
    padding-top: 72px; /* Space for fixed navbar */
  }
}


#skip-link {
  position: absolute;
  top: -50px;
}

#skip-link:focus {
  top: 0px;
  z-index: 2000;
  background: rgba(53, 50, 255, 0.7);
  color: white;
  padding-left: 3px;
}

</style>
