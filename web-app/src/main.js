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

import Vue from 'vue';
import App from './App.vue';
import VueResource from 'vue-resource';
import VueRouter from 'vue-router';
import 'intro.js/introjs.css'
import 'bootstrap';
import 'bootstrap/dist/css/bootstrap.min.css';
import Routes from './routes';


Vue.config.productionTip = false

Vue.use(VueResource)
Vue.use(VueRouter);

const router = new VueRouter({
  routes: Routes,
  mode: "history",
})

new Vue({
  render: h => h(App),
  router: router
}).$mount('#app')
