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
  <div class="container-fluid">
    <!-- leaflet -->

    <div class="row pt-4">
      <!-- left pane -->
      <div class="col-3" style="padding-right: 20px; height: 720px; overflow-y: scroll;">

        <div class="row pt-3">
          <h1>Checklist</h1>
          <table class="table table-sm table-hover" data-intro="This table will show you all errors and warnings that appear!
            Each issue will show you the criteria that failed, the severity, and information about the element that caused it.">
            <thead>
              <th class="text-center no-border-top" scope="col">Rule</th>
              <th class="text-center no-border-top" scope="col">Severity</th>
              <th class="text-center no-border-top" scope="col">Element</th>
            </thead>
            <tbody>
              <tr
                tabindex="0"
                v-for="v in active_atomic_violations"
                :key="createUniqueKey(v, '')"
                :ref="'tr-' + createUniqueKey(v, '')"
                v-on:click="setActiveViolation(v)"
                v-on:keyup.enter="setActiveViolation(v)"
                :class="{ 'active-warning-row': isActiveViolation(v) && isWarning(v.level),
                          'active-error-row': isActiveViolation(v) && isError(v.level)}"
              >
                <td class="text-center">{{ v.category }}</td>
                <td class="text-center font-weight-bold" v-bind:class="{'error-text': isError(v.level), 'warning-text': isWarning(v.level)}">{{ v.level }}</td>
                <td class="text-center">{{ v.element.tag }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- <div class="row pt-3">
          <h4>Grouped Violations</h4>
        </div>

        <div class="row">
          <article>
            <a
              class="btn btn-outline-info"
              data-toggle="collapse"
              href="#violation_group_details"
              role="button"
              aria-expanded="false"
              aria-controls="collapseExample"
            >
              Violation Group Details
            </a>
            <div class="collapse" id="violation_group_details">
              <div class="card card-body">
                A violation group means that solving any violation in the group will affect and possible solve other
                violations in the group. Note that this only referrs to violations as specified by the standards, but
                other errors such as usability issues may still exist.
              </div>
            </div>
          </article>
        </div>

        <div class="row">
          <table class="table table-sm table-hover">
            <thead>
              <th>Group Id</th>
              <th>Num Occurences</th>
              <th>States</th>
            </thead>
            <tbody>
              <tr
                v-for="group_id in Object.keys(violation_groups)"
                :key="group_id"
                :ref="'tr-' + group_id"
              >
                <td>{{ group_id }}</td>
                <td>{{ violation_groups[group_id].length }}</td>
                <td>{{ violation_groups[group_id] }} </td>
              </tr>
            </tbody>
          </table>
        </div> -->
      </div>

      <!-- right pane -->
      <div class="col-9" style="padding-left: 50px;">

        <!-- <div class="row"> -->
          <!-- <div class="col-4 form-group">
            <label for="select-state" class="text-nowrap">State Select</label>
            <select class="form-control" id="select-state" v-model="stateSelect">
              <option v-for="s in states" v-bind:key="s" v-bind:value="s">
                {{ s }}
              </option>
            </select>
          </div> -->

          <!-- <div class="col-5"> -->
            <!-- Pagination will pop up between states when a grouping of violations is selected -->
            <!-- <nav aria-label="Navigate between states" v-show="this.pagination_states.length > 1">
              <ul class="pagination" ref="state_pagination">
                <li class="page-item" id="page-prev">
                  <a class="page-link" v-on:click="paginationPrevState($event)" href="#">Previous</a>
                </li>
                <li class="page-item" v-for="state_id in this.pagination_states" :key="state_id">
                  <a
                    class="page-link"
                    :class="applyActiveStateClass(state_id)"
                    v-on:click="navigateToState(state_id)"
                    href="#"
                    >State {{ state_id }}</a
                  >
                </li>
                <li class="page-item" id="page-next">
                  <a class="page-link" v-on:click="paginationNextState($event)" href="#">Next</a>
                </li>
              </ul>
            </nav>
          </div>
        </div> -->

        <div class="row pt-3" data-intro="This pane visualizes all interactions 
          flagged with accessibility violations and warnings as 'bubbles' overlaid on screenshots 
          of the website. The size of the bubble corresponds to the number of issues occuring at
          a given element. Zoom in to see more detail." data-step="2">
          <h2 class="text-left" style="font-size: 40px;">Explorer</h2>
          <div id="map">
            <!-- Leaflet map with calculated parameters to hold screenshot of web page -->
            <l-map
              ref="map"
              v-on:click="mapClicked($event)"
              :min-zoom="min_zoom"
              :max-zoom="max_zoom"
              :crs="crs"
              :zoom="-1"
              :center="center"
            >
              <l-image-overlay :url="image_url" :bounds="bounds"></l-image-overlay>
              <!-- Allow users to pick which types of violations they want to see -->
              <l-control position="bottomleft" data-step="3" data-intro="Use these checkboxes to select
                which type of violations you would like to see presented.">
                <div class="violation-boxes-wrapper">
                  <fieldset class="violation-boxes">
                    <label class="error-text leaf-label">
                      <input type="checkbox" value="error" checked v-model="checked_violation_types">
                      Errors
                    </label>
                    <label class="warning-text leaf-label">
                      <input type="checkbox" value="warning" checked v-model="checked_violation_types">
                      Warnings
                    </label>
                    <label class="composite-text leaf-label">
                      <input type="checkbox" value="composite" checked v-model="checked_violation_types">
                      Composites
                    </label>
                  </fieldset>
                </div>
              </l-control>

              <l-control position="topright" data-step="4" data-intro="Choose the state you would like to inpsect at any time.">
                <nav aria-label="Page navigation example">
                  <ul class="pagination">
                    <li class="page-item">
                      <a class="page-link" href="#" aria-label="Previous" @click="mapPrevState">
                        <span aria-hidden="true">&laquo;</span>
                        <span class="sr-only">Previous</span>
                      </a>
                    </li>
                    <li>
                        <label for="select-state" class="text-nowrap sr-only">State Select</label>
                        <select class="form-control" id="select-state" v-model="stateSelect">
                          <option v-for="s in states" v-bind:key="s" v-bind:value="s">
                            {{ s }}
                          </option>
                        </select>
                    </li>
                    <li class="page-item">
                      <a class="page-link" href="#" aria-label="Next" @click="mapNextState">
                        <span aria-hidden="true">&raquo;</span>
                        <span class="sr-only">Next</span>
                      </a>
                    </li>
                  </ul>
                </nav>
              </l-control>

              <!-- Create cluster that holds violations of various types -->
              <v-marker-cluster :options="cluster_options" :ref="'marker-cluster'">
                <l-marker
                  v-for="v in active_atomic_violations"
                  :key="createUniqueKey(v, 'marker-atomic')"
                  :ref="'marker-' + createUniqueKey(v, '')"
                  :icon="markerIcon(v)"
                  :lat-lng="toLatLng(v.element)"
                  v-on:click="setActiveViolation(v)"
                  v-on:keyup.enter="setActiveViolation(v)"
                  :options="{level: v.level}"
                >
                  <l-popup :content="generatePopUpText(v)" />
                </l-marker>
                <l-marker
                  v-for="v in active_composite_violations"
                  :key="createUniqueKey(v, 'marker-comp')"
                  :icon="markerIcon(v)"
                  :lat-lng="toLatLng(v.element)"
                  v-on:click="navigateToState(v.state_link)"
                  v-on:keyup.enter="navigateToState(v.state_link)"
                  :options="{level: v.level}"
                >
                </l-marker>
              </v-marker-cluster>
              
              <!-- Highlight element for active violation -->
              <l-polygon
                :ref="'bounding_box'"
                :color="polygon_options.color"
                :fillColor="polygon_options.fillColor"
                :lat-lngs="active_bounding_box"
              ></l-polygon>
            </l-map>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import L from "leaflet";
import { CRS } from "leaflet";
import { LMap, LMarker, LImageOverlay, LControl } from "vue2-leaflet";
import Vue2LeafletMarkerCluster from 'vue2-leaflet-markercluster';

export default {
  name: "IssueExplorer",
  components: {
    LMap,
    LMarker,
    LImageOverlay,
    'v-marker-cluster': Vue2LeafletMarkerCluster,
    LControl
  },
  data() {
    return {
      base_url: "/crawls/" + this.$route.params.crawl,
      image_url: "",
      crs: CRS.Simple,
      min_zoom: -3,
      max_zoom: 2,
      element_map: [],
      current_state: 0,
      active_violation: {}, // TODO: Should we clear when going to new state
      active_bounding_box: [[0, 0]],
      active_group_id: -1,
      image: { width: 0, height: 0 },
      cluster_options: {
        iconCreateFunction: this.clusterIcon,
        showCoverageOnHover: false,
        disableClusteringAtZoom: 2,
      },
      polygon_options: {
        color: '',
        fillColor: '',
      },
      checked_violation_types: ["error", "warning", "composite"],
    };
  },
  methods: {
    paginationPrevState(event) {
      let pagination = this.$refs.state_pagination;

      // Get currently active child
      let activeChild = pagination.querySelector(".active");
      let prevSibling = activeChild.parentNode.previousSibling;

      // Check if previous child exists (is not the previous button itself)
      if (prevSibling.getAttribute("id") !== "page-prev") {
        prevSibling.firstChild.click(); // Activate the previous state
      }

      event.preventDefault();
    },
    paginationNextState(event) {
      let pagination = this.$refs.state_pagination;

      // Get currently active child
      let activeChild = pagination.querySelector(".active");
      let nextSibling = activeChild.parentNode.nextSibling;

      if (nextSibling.getAttribute("id") !== "page-next") {
        nextSibling.firstChild.click(); // Activate next state
      }

      event.preventDefault();
    },
    /**
     * Right now the state_id equals its index in the states array
     * The methods below try to be a bit more robust if this isn't the
     * case to make sure we don't go out of array bounds
     */
    mapPrevState() {
      let currentStateIndex = this.states.indexOf("" + this.current_state);
      // Check if there are prior states
      if (currentStateIndex != 0) {
        this.stateSelect = this.states[currentStateIndex - 1];
      }
      // Otherwise do nothing
    },
    mapNextState() {
      
      let currentStateIndex = this.states.indexOf("" + this.current_state); // State ids held as strings
      // If the current state is not at the end of the array, get the next state id
      if (!(currentStateIndex == this.states.length - 1)) {
        this.stateSelect = this.states[currentStateIndex + 1];
      }
      // Otherwise do nothing, there is no next state
    },
    /**
     * There should only be one active violation at any time. This is to 
     * focus users on a specific issue. When a violation is set, several things
     * should happen:
     * - The table row corresponding to this violation is highlighted
     * - The marker is zoomed in on if not already
     * - A bounding box around the offending element is drawn
     */
    setActiveViolation(violation) {

      console.log("Setting active violation");
      this.active_violation = violation;
      this.active_group_id = violation.group_id;

      // Create bounding box around the element in this violation
      this.setActiveBoundingBox(violation);

      /**
       * DYNAMICALLY SET THE VIEW
       * Rows in the table and markers on the map have semi-shared keys.
       * These follow the form:
       * Table - "tr-{unique_violation_key}"
       * Marker - "mark-{unique_violation_key}"
       */
      let markerRefKey = "marker-" + this.createUniqueKey(violation, '');
      this.$refs["marker-cluster"].mapObject.zoomToShowLayer(this.$refs[markerRefKey][0].mapObject);
    },
    // TODO: Can uses of this function be replaced by this.stateSelect = state_link? Or
    // are there cases we may want to do some extra processing before making the switch?
    navigateToState(state_link) {
      this.stateSelect = state_link;
    },
    /**
     * Function determines the size and color of the cluster marker depending on the children.
     * Currently, an error-win-all system, where if a cluster has any error children, then
     * the whole cluster becomes red (possibly misleadingly). Additionally, the size of
     * the cluster will grow as more children are added. Currently, this growth is unbounded.
     */
    clusterIcon(cluster) {
      let childCount = cluster.getChildCount();
      let childMarkers = cluster.getAllChildMarkers();
      let clusterType = "warning"; // Default
      let markerImg = this.markerWarningImage(12);

      // Check all child markers, if any are error then consider the whole cluster an error
      let errors = childMarkers.filter((marker) => {return marker.options.level == "error"});
      if (errors.length > 0) {
        clusterType = "error"
        markerImg = this.markerErrorImage(12);
      }

      // Scale Icon Size with number of children
      let iconSize = 40 + 4 * childCount;

      return new L.DivIcon({ 
        html: `<div><span>${markerImg}${childCount}</span></div>`, 
        className: `scalable-marker-cluster marker-cluster-${clusterType}`, 
        iconSize: new L.Point(iconSize, iconSize) });
    },
    // Follows same guidelines as the clusterIcon above, marker icons are just considered seperate
    markerIcon(violation) {

      // Change color depending on if the violation is a warning or error
      let markerImg = this.markerWarningImage(10);
      let markerIconType = "marker-cluster-warning";
      if (violation.type == "composite") {
        markerIconType = "marker-cluster-composite";
        markerImg = "";
      }
      else if (violation.level == "error") {
        markerIconType = "marker-cluster-error"
        markerImg = this.markerErrorImage(10);
      }

      // Special formatting for active violations
      if (this.active_violation == violation) {
        if (violation.level == "warning") {
          markerIconType = "active-marker-cluster-warning";
        }
        else if (violation.level == "error") {
          markerIconType = "active-marker-cluster-error";
        }
      }

      return new L.DivIcon({ 
        html: `<div><span>${markerImg}</span></div>`, className: 'marker-cluster ' + markerIconType, iconSize: new L.Point(40, 40) });

    },
    // Convert an elements position to lat and long
    toLatLng(element) {
      
      let x = Number(element.x);
      let y = Number(element.y);
      let width = Number(element.width);

      // return [this.image.height - 2 * y, 2 * x + 0.5 * width * 2]; // Use width to get center

      return [this.image.height - y, x + 0.5 * width]; // Use width to get center
    },
    /**
     * Given an element, calculates the bounding box for use in creating a polygon
     * around the element on the map.
     */
    setActiveBoundingBox(violation) {

      // Determine bounding box size
      let element = violation.element;
      let x = Number(element.x);
      let y = Number(element.y);
      let width = Number(element.width);
      let height = Number(element.height);

      if (width === 0 && height === 0) {
        return [[0, 0]]; // No bounding box
      }

      // Make min height or width 5
      width = width < 5 ? 5 : width;
      height = height < 5 ? 5 : height;

      this.active_bounding_box = [
        [this.image.height - y, x],
        [this.image.height - y, x + width],
        [this.image.height - y - height, x + width],
        [this.image.height - y - height, x],
      ];

      // Determine bounding box color
      if (this.isWarning(violation.level)) {
        this.polygon_options.color = "rgba(183, 156, 7, 0.8)"
        this.polygon_options.fillColor = "rgba(183, 156, 7, 0.2)"
      }
      else if (this.isError(violation.level)) {
        this.polygon_options.color = "rgba(166, 6, 6, 0.8)";
        this.polygon_options.fillColor = "rgba(166, 6, 6, 0.2)";
      }

    },
    generatePopUpText(violation) {
      // TODO: Calculate popup text to clarify what the violation element is and why
      // Ex. Read More Button, poor focused color contrast
      // Assumedly use a mix of the HTML tag, text content, and output violations
      let el = violation.element;
      let element_type = ""; // Type of element such as button or link
      let element_text = ""; // Text contained in element
      // let violation_cat = ""; // Type of violation found

      // TODO: Fill out with more cases
      switch (el.tag) {
        case "a":
          element_type = "Link";
          break;
        case "button":
          element_type = "Button";
          break;
        default:
          element_type = "Element";
          break;
      }

      if (el.text === null) {
        element_text = "";
      } else {
        element_text = el.text.trim() + " ";
      }

      return element_text + element_type;
    },
    createUniqueKey(violation, prefix) {
      // Generates unique keys for vue iteration
      // Elements can only have <= 1 composite issue
      if (violation["type"] === "composite") {
        return prefix + " composite " + violation.element.xpath;
      } else {
        // Elements could have multiple violation categories
        return prefix + " atomic " + violation.category + violation.element.xpath;
      }
    },
    isActiveViolation(v) {
      // NOTE: We are comparing the actual reference addresses here!
      if (this.active_violation) {
        return v == this.active_violation;
      }

      return false;
    },
    applyActiveStateClass(state_id) {
      return { active: this.current_state == state_id };
    },
    isError(level) {
      return level == "error";
    },
    isWarning(level) {
      return level == "warning";
    },
    markerWarningImage(size) {
      return `<img alt="Warning" style="width: ${size}px; height: ${size}px;" src="${require(`../assets/Warn.png`)}">`;
    },
    markerErrorImage(size) {
      return `<img alt="Error" style="width: ${size}px; height: ${size}px;" src="${require(`../assets/Error.png`)}">`;
    },
    mapClicked(event) {
      // FOR DEBUGGING ONLY
      console.log(event.latlng.lat + " " + event.latlng.lng);
    },
  },
  computed: {
    bounds() {
      return [
        [0, 0],
        [this.image.height, this.image.width],
      ];
    },
    center() {
      return [this.image.height - 380, 1000]; // TODO: Will this need adjusting?
    },
    elements() {
      if (Object.keys(this.element_map).length > 0) {
        return this.element_map[this.current_state]["violations"].map((violation) => violation["element"]);
      }
      return [];
    },
    violations() {
      if (Object.keys(this.element_map).length > 0) {
        return this.element_map[this.current_state]["violations"];
      }
      return [];
    },
    atomic_violations() {
      if (Object.keys(this.element_map).length > 0) {
        // Find the atomic violations
        return this.element_map[this.current_state]["violations"].filter((v) => v.type == "atomic");
      }
      return [];
    },
    active_atomic_violations(){
      return this.atomic_violations.filter(v => this.checked_violation_types.includes(v.level));
    },
    atomic_errors() {
      return this.atomic_violations.filter((v) => {return v.level == "error"});
    },
    atomic_warnings() {
      return this.atomic_violations.filter((v) => {return v.level == "warning"});
    },
    composite_violations() {
      if (Object.keys(this.element_map).length > 0) {
        return this.element_map[this.current_state]["violations"].filter((v) => v.type == "composite");
      }
      return [];
    },
    active_composite_violations() {
      if (this.checked_violation_types.includes("composite")) {
        return this.composite_violations;
      }
      return [];
    },
    violation_groups() {
      // Calculate which state different violations groups appear on
      let violation_groups = {};

      for (let state_id in Object.keys(this.element_map)) {
        let state = this.element_map[state_id];

        for (let violation of state["violations"]) {
          if (!violation["group_id"]) {
            // If group id is undefined, skip
            continue;
          }

          let id = violation["group_id"];
          // If id has not been added
          if (!(id in violation_groups)) {
            violation_groups[id] = [];
          }

          // Check if this state has already been added for the group
          if (!violation_groups[id].includes(state_id)) {
            violation_groups[id].push(state_id);
          }
        }
      }

      return violation_groups;
    },
    states() {
      let st = Object.keys(this.element_map);

      st.sort(function(a, b) {
        return Number(a) - Number(b);
      });
      return st;
    },
    pagination_states() {
      // States that should show up in the pagination prompt
      return this.violation_groups[this.active_group_id] || [];
    },
    stateSelect: {
      get: function() {
        return this.current_state;
      },
      set: function(state_id) {

        // Set currently state and image url
        this.current_state = state_id;
        this.active_bounding_box = [[0, 0]];
        this.image_url = this.base_url + "/screenshots/state-" + state_id + ".png";

        // Get size of image TODO: We have to load this seperately, anyways to get it from leaflets load?
        let loadImage = new Image();
        loadImage.self = this;
        loadImage.onload = () => {
          let image = loadImage.self.image;
          image.width = loadImage.naturalWidth;
          image.height = loadImage.naturalHeight;
          console.log(image.width + " " + image.height);
        };

        // this.image.url = image_url;
        loadImage.src = this.image_url;
      },
    },
  },
  created: async function() {
    let elMapUrl = this.base_url + "/element_map.json";

    try {
      let response = await this.$http.get(elMapUrl);
      this.element_map = response.body;
      // console.log(this.element_map);
      if (Object.keys(this.element_map).length > 0) {
        this.current_state = Object.keys(this.element_map)[0]; // Will this just always be 0?
      }
    } catch (e) {
      console.log("Error getting data.", e);
    }

    this.stateSelect = 0; // Default start state
  },
};
</script>

<style>
.scalable-marker-cluster {
    border-radius: 50%;
    display: flex;
    justify-content: center;
    align-items: center;
}

.scalable-marker-cluster div {
  height: 85%;
  width: 85%;
  border-radius: 50%;
  display: flex;
  justify-content: center;
  align-items: center;
}

.marker-cluster-error {
  background: #a60606;
}

.marker-cluster-error div {
  background: #f6e6e6
}

.active-marker-cluster-error {
  background: #a60606;
}

.active-marker-cluster-error div {
  background: #a60606;
}

.marker-cluster-warning {
  background: #b79c07;
  /* background: lightyellow; */
}

.marker-cluster-warning div {
  background: lightyellow;
}

.active-marker-cluster-warning {
  background: #b79c07;
}

.active-marker-cluster-warning div {
  background: #b79c07;
}

.marker-cluster-composite {
  background: #596156;
}

.marker-cluster-composite div {
  background: whitesmoke;
}

.active-error-row {
  background: rgba(166, 6, 6, 0.2);
}

.active-warning-row {
  background: rgba(183, 156, 7, 0.2);
}

</style>

<style scoped>
@import "~leaflet.markercluster/dist/MarkerCluster.css";
@import "~leaflet.markercluster/dist/MarkerCluster.Default.css";

#map {
  width: 100%;
  height: 650px;
}

hr {
  width: 1px;
  height: 1000px;
  background: black;
}

.centered-title {
  width: 100%;
  text-align: center;
}


.active {
  background: #f88;
}

.violation-boxes {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,"Noto Sans",sans-serif,"Apple Color Emoji","Segoe UI Emoji","Segoe UI Symbol","Noto Color Emoji";
  padding-top: 10px;
  padding-left: 10px;
  padding-right: 10px;
  padding-bottom: 5px;
}

input[type=checkbox] {-webkit-appearance: checkbox;}

.violation-boxes-wrapper {
  border: none;
  background: white;
  border-radius: 4px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.2)
}

.leaflet-container {
    background: #f8f9fa;
    outline: 0;
    border-radius: 4px;
    border: solid 2px #eee;
}

.leaflet-bar {
    box-shadow: 0 1px 3px rgba(0,0,0,0.2);
    border-radius: 4px;
    border: none;
}

ul.pagination {
  border: none;
  font-size: 15px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.2);
}

.leaf-label {
  font-weight: bold;
  font-size: 15px;

}

.error-text {
  color: #BB1625;
}

.warning-text {
  color:  #867203;
}

.composite-text {
  color: #596156;
}

.no-border-top {
  border-top: none;
}

#select-state {
  border-radius: 0rem !important;
  z-index: 1000;
}

*:focus {
  border: 3px solid black;
}

</style>
