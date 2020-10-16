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
      <h1 class="centered-title">Dashboard</h1>
    </div>

    <div class="row pt-4">
      <!-- DASHBOARD TABLE -->
      <!-- Right align for numbers -->
      <!-- Border styling between sections, sections should have same cell size -->
      <table class="table table-bordered table-fixed">
        <thead>
          <tr class="dashboard-table-head">
            <th>Page Url</th>
            <th>
              <div class="head-cell">
                <img src="../assets/HomeSm.png" alt="" />
                Total
              </div>
            </th>
            <th class="error">
              <div class="head-cell">
                <img src="../assets/Error.png" alt="" />
                Errors
              </div>
            </th>
            <th class="warning solid-border-right">
              <div class="head-cell">
                <img src="../assets/Warning.png" alt=""/>
                Warnings
              </div>
            </th>
            <th>
              <div class="head-cell">
                <img src="../assets/magnify-plus-outline.png" alt=""/>
                Visual
              </div>
            </th>
            <th>
              <div class="head-cell">
                <img src="../assets/mouse.png" alt=""/>
                Mouse
              </div>
            </th>
            <th class="solid-border-right">
              <div class="head-cell">
                <img src="../assets/UsersSm.png" alt=""/>
                Keyboard
              </div>
            </th>
            <th>
              <div class="head-cell">
                <img src="../assets/Chrome.png" alt=""/>
                Browser
              </div>
            </th>
            <th>
              <div class="head-cell">
                <img src="../assets/calendar-month-outline.png" alt=""/>
                Date
              </div>
            </th>
            <th>
              <div class="head-cell">
                <img src="../assets/percent.png" alt=""/>
                Percent Change
              </div>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="crawl in crawl_data" :key="crawl['page_url']">
            <td class="text-break">
              <router-link :to="'/explorer/' + crawl['page_url']" class="dem-color"><b>{{ crawl["page_url"] }}</b></router-link>
            </td>
            <td class="text-right">
              {{ crawl["total_violations"] }}
            </td>
            <td class="error text-right">{{ crawl["num_errors"] }}</td>
            <td class="warning text-right solid-border-right">{{ crawl["num_warnings"] }}</td>
            <td class="text-right">{{ crawl["num_visual"] }}</td>
            <td class="text-right">{{ crawl["num_mouse"] }}</td>
            <td class="text-right solid-border-right">{{ crawl["num_keyboard"] }}</td>
            <td class="text-center">{{ crawl["browser"] }}</td>
            <td class="text-center">{{ crawl["date"] }}</td>
            <td class="text-right">{{ crawl["percent_change"] }}</td>
          </tr>
        </tbody>
      </table>
    </div>

  </div>
</template>

<script>
export default {
  name: "Dashboard",
  components: {},
  data() {
    return {
      crawls_names: JSON.parse(process.env.VUE_APP_CRAWL_FOLDERS), // In practice should be from db
      crawls: {}, // Populated in created
      crawl_data: [], // Formatted crawls into table ready data format
      base_url: "/crawls/",
    };
  },
  methods: {
    // Calculate data for table fields
    calculateCrawlData() {
      let crawl_data = [];

      for (let crawl_name in this.crawls) {
        let crawl = this.crawls[crawl_name];
        let data = {};

        // Page Url
        data["page_url"] = crawl_name;
        // Violation metrics
        let violations = this.getAllViolations(crawl);
        data["total_violations"] = violations.length;
        data["num_errors"] = violations.filter((v) => v.level == "error").length;
        data["num_warnings"] = violations.filter((v) => v.level == "warning").length;

        // User type category
        // 2.5.5 - Target Size mouse
        // 2.4.7 - Focus Visible
        // 2.1.1 - Keyboard accessible
        data["num_visual"] = violations.filter((v) => v.category == "S.C. 2.4.7").length;
        data["num_mouse"] = violations.filter((v) => v.category == "S.C. 2.5.5").length;
        data["num_keyboard"] = violations.filter((v) => v.category == "S.C. 2.1.1").length;

        // Browser (dummy data for now)
        data["browser"] = "v80.0.3987";
        // Date (dummy data for now)
        data["date"] = "7/12/20";
        // Change (dummy data for now)
        data["percent_change"] = Math.floor(Math.random() * 50);

        crawl_data.push(data);
      }

      this.crawl_data = crawl_data;
    },
    getAllViolations(crawl) {
      let violations = [];

      // Accumulate violations from each state
      for (let state in crawl) {
        violations = violations.concat(crawl[state]["violations"]);
      }

      return violations;
    },
  },
  created: async function() {
    // GET DATA FROM ALL CRALWS IN this.crawl_names

    for (let crawl_name of this.crawls_names) {
      let elMapUrl = this.base_url + crawl_name + "/element_map.json";

      try {
        let response = await this.$http.get(elMapUrl);
        this.crawls[crawl_name] = response.body;
      } catch (e) {
        console.log("Error getting data. ", e);
      }
    }

    // Transforms data received here into data for table
    this.calculateCrawlData();
  },
};
</script>

<style scoped>
.centered-title {
  width: 100%;
  text-align: center;
}

.head-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.head-cell img {
  height: 20px;
}

.dem-color {
  color: #004ea2;
}

.error {
  color: #BB1625;
  font-weight: bold;
}

.warning {
  color: #867203;
  font-weight: bold;
}

.solid-border-right {
  border-right: 2px solid #aaa;
}

.table-fixed {
  table-layout: fixed;
}
</style>
