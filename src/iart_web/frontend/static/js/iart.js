// import AnchoredHeading from './AnchoredHeading.vue'
import Vue from 'vue';
import Vuex from 'vuex';
import Vuetify from 'vuetify';
import VueIntro from 'vue-introjs';

import 'vuetify/dist/vuetify.min.css';
import 'intro.js/introjs.css';

import * as THREE from 'three';
import * as TWEEN from '@tweenjs/tween.js'
import { Interaction } from 'three.interaction';
import { TrackballControls } from 'three/examples/jsm/controls/TrackballControls';

Vue.use(Vuex);
Vue.use(Vuetify);
Vue.use(VueIntro);

Vue.mixin({
  data: function() {
    return {
      get url_static() {
        
        return url_static;
      }
    }
  }
})

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

const store = new Vuex.Store({
  state: {
    suggestions: [],
    entries: [],
    user: null,
    selected: null,
    sorting: null,

    search: {
      job_id: null,
      status: null,
      polling_job: null,
    },

    weights: {
      yuv_histogram_feature: 0.0,
      byol_embedding_feature: 0.0,
      image_net_inception_feature: 0.0,
      clip_embedding_feature: 1.0,
    },

    query: {},
    categories: [],
    features: [],
    reference: [],
    zoomLevel: 0,
    meshSize: 1.3,
    submit: false,

    layout: {
      width: "auto",
      height: 200,
      mapping: null,
    },

    dialog: false,

    feature_list: [],
  },
  mutations: {
    updateSuggestions(state, suggestions) {
      state.suggestions = suggestions;
    },
    updateQuery(state, query) {
      state.query = query;
    },
    updateEntries(state, entries) {
      state.entries = entries;
    },
    updateSelected(state, entry) {
      state.selected = entry;
    },
    updateReference(state, entry) {
      state.reference = [entry];
    },
    updateSearch(state, search) {
      if (!!state.search.polling_job) {
        clearInterval(state.search.polling_job);
      }
      state.search = search;
    },
    updateZoomLevel(state, level) {
      state.zoomLevel = level;
    },
    updateMeshSize(state, size) {
      state.meshSize = size;
    },
    updateLayout(state, layout) {
      state.layout = layout;
    },
    updateWeights(state, weights) {
      state.weights = weights;
    },
    updateSorting(state, sorting) {
      state.sorting = sorting;
    },
    updateDialog(state, dialog) {
      state.dialog = dialog;
    },
    updateFeatureList(state, feature_list) {
      state.feature_list = feature_list;
      console.log(feature_list);
    },
    toggleSubmit(state) {
      state.submit = !state.submit;
    },
  },
  actions: {
    refreshAutocomplete(context, parameter) {
      // console.log('start fetch');
      // console.log(parameter.query);
      fetch(url_autocomplete, {
        method: "POST",
        headers: {
          "X-CSRFToken": csrftoken,
          "Content-Type": "application/json",
          // 'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: JSON.stringify({
          query: parameter.query,
        }),
      })
        .then(function (res) {
          return res.json();
        })
        .then(function (data) {
          if (data.status == "ok") {
            context.commit("updateSuggestions", data["suggestions"]);
            // console.log('update suggestions');
          } else {
            console.log("error");
          }
        })
        .catch((error) => {
          // console.log('error');
          // console.log(error);
        });
    },
    search(context, parameter) {
      var that = this;

      fetch(url_search, {
        method: "POST",
        headers: {
          "X-CSRFToken": csrftoken,
          "Content-Type": "application/json",
          // 'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: JSON.stringify({
          queries: parameter.queries,
          sorting: parameter.sorting,
          mapping: parameter.mapping,
        }),
      })
        .then(function (res) {
          return res.json();
        })
        .then(function (data) {
          if (data.status == "ok") {
            var polling_job = setInterval(
              function () {
                // that.listSearchResults();

                that.dispatch("listSearchResults", {
                  // features: this.weights,
                  // reference: this.$store.state.selected
                });
              }.bind(that),
              200
            );

            context.commit("updateSearch", {
              job_id: data.job_id,
              status: "running",
              polling_job: polling_job,
            });
          } else {
            console.log("error");
          }
        })
        .catch((error) => {
          console.log("error");
          console.log(error);
        });
    },
    upload(context, parameter) {
      var that = this;

      var data = new FormData()
      data.append('file', parameter.file)
      data.append('url', parameter.url)

      fetch(url_upload, {
        method: "POST",
        headers: {
          "X-CSRFToken": csrftoken,
          // "Content-Type": "application/json"
          // 'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: data
      })
        .then(function (res) {
          return res.json();
        })
        .then(function (data) {
          if (data.status == "ok") {
            // TODO several entries from upload
            context.commit("updateQuery", {
              name: data.entries[0], group: "image",
            });

            context.commit("toggleSubmit");
          } else {
            console.log("error");
          }
        })
        .catch((error) => {
          console.log("error");
          console.log(error);
        });
    },
    listFeatures(context, parameter) {
      console.log('FOOBAR');
      var that = this;

      fetch(url_list_features, {
        method: "POST",
        headers: {
          "X-CSRFToken": csrftoken,
          "Content-Type": "application/json",
          // 'Content-Type': 'application/x-www-form-urlencoded',
        },
      })
        .then(function (res) {
          return res.json();
        })
        .then(function (data) {
          if (data.status == "ok") {
            context.commit("updateFeatureList", data.features);
          } else {
            console.log("error");
          }
        })
        .catch((error) => {
          console.log("error");
          console.log(error);
        });
    },
    listSearchResults(context, parameter) {
      fetch(url_search_result, {
        method: "POST",
        headers: {
          "X-CSRFToken": csrftoken,
          "Content-Type": "application/json",
          // 'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: JSON.stringify({
          id: this.state.search.job_id,
        }),
      })
        .then(function (res) {
          return res.json();
        })
        .then(function (data) {
          if (data.status == "running") {
            return
          }
          console.log(data);

          context.commit("updateSearch", {
            job_id: null,
            status: null,
            polling_job: null,
          });

          // context.commit('updateReference', parameter.reference)
          context.commit("updateEntries", data["entries"]);
          window.scrollTo(0, 0);
        })
        .catch((error) => {
          console.log("error");
          console.log(error);
        });
    },
  },

});


function capitalize(x) {
  if (typeof x !== "string") return x;
  return x.charAt(0).toUpperCase() + x.slice(1);
}

Vue.component("umap", {
  template: `
    <div class="umap">
      <div class="canvas"></div>
    </div>`,
  data: function () {
    return {
      canvasSize: 100,
      timer: null,
      nStep: 8,
    };
  },
  mounted: function () {
    this.init();
    this.controls();
    this.animate();
  },
  computed: {
    entries: function () {
      return this.$store.state.entries;
    },
    meshSize: function () {
      return this.$store.state.meshSize;
    },
    zoomLevel: function () {
      return this.$store.state.zoomLevel;
    },
    zoomStep: function () {
      return this.canvasSize / this.nStep;
    }
  },
  methods: {
    init: function () {
      const [width, height] = this.getSize();

      this.scene = new THREE.Scene();
      this.scene.background = new THREE.Color(0xe0e0e0);

      this.camera = new THREE.PerspectiveCamera(
        0.5 * this.canvasSize, width / height
      );

      this.resetCamera(0, 0, 12 * this.zoomStep);

      this.renderer = new THREE.WebGLRenderer({antialias: true});
      this.renderer.setPixelRatio(window.devicePixelRatio);
      this.renderer.setSize(width, height);

      const canvas = document.querySelector(".umap .canvas");
      canvas.appendChild(this.renderer.domElement);

      window.addEventListener("resize", this.onResize);

      const interaction = new Interaction(
        this.renderer, this.scene, this.camera
      );
    },
    controls: function () {
      this.controls = new TrackballControls(
        this.camera, this.renderer.domElement
      );

      this.controls.dynamicDampingFactor = 0.1;
      const ALT_KEY = 18, CTRL_KEY = 17, CMD_KEY = 91;
      this.controls.keys = [ALT_KEY, CTRL_KEY, CMD_KEY];

      this.controls.minDistance = 2 * this.zoomStep;
      this.controls.maxDistance = 14 * this.zoomStep;

      this.controls.mouseButtons = {
        LEFT: THREE.MOUSE.PAN,
        MIDDLE: THREE.MOUSE.ZOOM,
        RIGHT: THREE.MOUSE.ROTATE,
      };

      this.renderer.domElement.addEventListener(
        "wheel", this.onWheel, false  // zoom event
      );
    },
    animate: function () {
      requestAnimationFrame(this.animate);
      this.controls.update(); TWEEN.update();
      this.renderScene();
    },
    getTexture: function (entry) {
      const loader = new THREE.TextureLoader()
      
      return new Promise((resolve, reject) => {
        loader.load(
          entry.path, texture => resolve(texture),
          undefined, error => reject(error)
        )
      })
    },
    addMesh: function (entry, type) {
      this.getTexture(entry).then(texture => {
        let width = texture.image.width, 
            height = texture.image.height,
            [x, y, z] = entry.coordinates;

        if (type == "cylinder") {
          texture.wrapS = THREE.ClampToEdgeWrapping;
          texture.wrapT = THREE.RepeatWrapping;

          if (width > height) {
            texture.repeat.set(height / width, 1);
            texture.offset.x = 0.5 * (1 - height / width);
          } else {
            texture.repeat.set(1, width / height);
            texture.offset.y = 0.5 * (1 - width / height);
          }

          var geometry = new THREE.CylinderBufferGeometry(
            this.meshSize, this.meshSize, 0.05, 48
          );
        } else if (type == "plane") {
          if (width > height) {
            height /= width / this.meshSize; 
            width = this.meshSize;
          } else {
            width /= height / this.meshSize; 
            height = this.meshSize;
          }

          var geometry = new THREE.BoxBufferGeometry(
            width, height, 0.05, 1, 1, 1
          );
        }

        let material = new THREE.MeshBasicMaterial({map: texture});
        let mesh = new THREE.Mesh(geometry, material);

        mesh.position.setX((x - 0.5) * this.canvasSize);
        mesh.position.setY((y - 0.5) * this.canvasSize);

        if (z != undefined) {
          mesh.position.setZ((z - 0) * this.canvasSize);
        }

        if (type == "cylinder") {
          mesh.rotation.set(Math.PI / 2, Math.PI / 2, 0);
        }

        mesh.entry = entry; 
        mesh.cursor = "pointer";
        mesh.on("click", this.onClick);

        this.scene.add(mesh);
      });
    },
    getSize: function() {
      let width = document.querySelector(".umap").clientWidth;
      let height = document.querySelector(".umap").clientHeight;

      return [width, height];
    },
    renderScene: function () {
      this.renderer.render(this.scene, this.camera);
    },
    resetCamera: function (x, y, z) {
      let position = {x: x, y: y, z: z};

      new TWEEN.Tween(this.camera.position)
        .to(position, 750)
        .easing(TWEEN.Easing.Quadratic.In)
        .onComplete(function() {
          this.camera.position.copy(position);
        }.bind(this))
        .start();
    },
    resetControls: function (x, y, z) {
      let position = {x: x, y: y, z: z};

      new TWEEN.Tween(this.controls.target)
        .to(position, 750)
        .easing(TWEEN.Easing.Quadratic.In)
        .onComplete(function() {
          this.controls.target.copy(position);
          this.controls.update();
        }.bind(this))
        .start();
    },
    resetScene: function () {
      while (this.scene.children.length) {
        this.scene.remove(this.scene.children[0]);
      }

      if (this.entries != undefined) {
        for (let i = 0; i < this.entries.length; i++) {
          if (this.entries[i].coordinates.length > 1) {
            this.addMesh(this.entries[i], "plane");
          }
        }
      }
    },
    onResize: function () {
      if (document.querySelector(".umap") != null) {
        let [width, height] = this.getSize();

        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();

        this.renderer.setSize(width, height);
      }
    },
    onClick: function (event) {
      if (event.data.originalEvent.detail === 1) {
        this.timer = setTimeout(function () {
          let entry = event.data.target.entry;

          this.$store.commit("updateSelected", entry);
          this.$store.commit("updateDialog", "detail");
        }.bind(this), 250);
      } else {
        clearTimeout(this.timer); TWEEN.removeAll();

        let x = event.data.target.position.x,
            y = event.data.target.position.y,
            z = event.data.target.position.z;

        this.resetCamera(x, y, z + 1.5 * this.meshSize);
        this.resetControls(x, y, 0);
      }
    },
    onWheel: function (event) {
      setTimeout(function () {
        let z = this.camera.position.z / this.zoomStep;
        let zoomLevel = -Math.floor(z - this.nStep);

        this.$store.commit("updateZoomLevel", zoomLevel);
      }.bind(this), 250);
    },
  },
  watch: {
    entries: function () {
      this.resetCamera(0, 0, 12 * this.zoomStep); 
      this.resetControls(0, 0, 0); 
      this.resetScene();
    },
    meshSize: function () {
      this.resetScene();
    },
    zoomLevel: function (value) {
      // TODO: zoom in or out on button click
    },
  },
});

Vue.component("gallery", {
  template: `
    <div class="grid-view open pa-1">
      <gallery-item v-for="entry in entries" :key="entry.id" :entry="entry"/>
    </div>`,
  computed: {
    entries: function () {
      return this.$store.state.entries;
    },
  },
});

Vue.component("gallery-item", {
  template: `
    <div class="grid-item" :disabled="disabled" :style="getCss">
      <img :src="entry.path" v-on:error="onError"></img>

      <div class="overlay">
        <div class="view">
          <v-menu offset-y bottom right>
            <template v-slot:activator="{ attrs, on: menu }">
              <v-btn icon v-bind="attrs" v-on="menu" title="Search for similar objects">
                <v-icon color="white" class="shadow">mdi-image-search-outline</v-icon>
              </v-btn>
            </template>

            <v-list>
              <v-list-item>
                <v-btn text @click="search(false)">Launch new search</v-btn>
              </v-list-item>

              <v-list-item>
                <v-btn text @click="search(true)">Append to search</v-btn>
              </v-list-item>
            </v-list>
          </v-menu>
          <v-btn icon @click="openDetail" title="View object">
            <v-icon color="white" class="shadow">mdi-eye-outline</v-icon>
          </v-btn>
        </div>

        <div class="meta">
          <div v-if="title" class="text-subtitle-1" :title="title">{{title}}</div>
          <div v-if="artist" class="text-caption" :title="artist">{{artist}}</div>
        </div>
      </div>
    </div>`,
  props: ["entry"],
  data: function () {
    return {
      disabled: false,
    };
  },
  computed: {
    title: function() {
      var title = [] 
      this.entry.meta.forEach(element => {
        if(element.name == "title"){
          title.push(element.value_str)
        }
      });
      return title.join(', ')
    },
    artist: function(){
      var artist = [] 
      this.entry.meta.forEach(element => {
        if(element.name == "artist_name"){
          artist.push(element.value_str)
        }
      });
      return artist.join(', ')
    },
    updateHeight: function () {
      var height = this.$store.state.layout.height;

      return height + this.$store.state.zoomLevel * 25;
    },
    updateWidth: function () {
      var width = this.$store.state.layout.width;
      var height = this.$store.state.layout.height;

      if (typeof width === "string") return width;

      if (width == height) {
        width += this.$store.state.zoomLevel * 25;
      }

      return width + "px";
    },
    getCss: function () {
      return {
        "--item-height": this.updateHeight + "px",
        "--item-width": this.updateWidth,
      }
    },
  },
  methods: {
    onError (element) {
      this.disabled = true;
    },
    search(add) {
      this.$store.commit("updateQuery", {
        name: this.entry, group: 'image', 
        add: add,  // add item to search bar
      });

      this.$store.commit("toggleSubmit");
    },
    openDetail: function () {
      this.$store.commit("updateSelected", this.entry);
      this.$store.commit("updateDialog", "detail");
    }
  },
});

Vue.component("detail-view", {
  template: `
    <v-dialog v-model="dialog" max-width="800px">
      <v-card v-if="entry!=null">
        <div class="img-wrapper">
          <v-img 
            :lazy-src="entry.path" :src="entry.path" class="grey lighten-1" 
            :max-height="isWide? 'auto' : '500px'" contain
          >
            <template v-slot:placeholder>
              <v-row class="fill-height ma-0" align="center" justify="center">
                <v-progress-circular indeterminate></v-progress-circular>
              </v-row>
            </template>
          </v-img>

          <v-btn icon @click="close" absolute top right>
            <v-icon>mdi-close</v-icon>
          </v-btn>

          <detail-view-menu :item="entry" type="image" @closeDialog="close"/>
        </div>

        <v-card-title class="mb-2 mr-16">
          <div class="text-h5 max-w">
            <span v-if="!title">No title</span>

            <span v-else v-for="word in title">
              <detail-view-menu :item="word" type="meta" @closeDialog="close"/>
            </span>
          </div>

          <div class="text-h6 max-w font-weight-regular grey--text mt-1">
            <span v-if="!artist">Unknown</span>

            <span v-else>
              {{artist}}

              <v-btn 
                icon @click="searchArtist(artist)" class="ml-1" 
                title="Search for the artist" depressed small
              >
                <v-icon size="20">mdi-link-variant</v-icon>
              </v-btn>
            </span>
          </div>
        </v-card-title> 

        <v-card-text>
          <v-chip v-if="date" class="mr-1 mb-1" :title="date">
            <v-icon left>mdi-clock-time-four-outline</v-icon>{{date}}
          </v-chip>

          
          <v-chip 
            v-for="anno in annotations" :key="'anno'+anno.id" class="mr-1 mb-1"  outlined
          >
            <detail-view-menu :item="anno.name" type="meta" @closeDialog="close"/>
          </v-chip>

          

          <v-chip 
            v-for="tag in tags" :key="'tag'+tag.id" class="mr-1 mb-1" 
            :text-color="tag.disable ? 'grey lighten-1' : ''" outlined
          >
            <span :title="tag.name">{{tag.name}}</span>
            <v-icon v-if="tag.disable" class="ml-1 mr-n1" size="14">mdi-help</v-icon>
            <detail-view-menu :item="tag.name" type="annotations" @closeDialog="close"/>
          </v-chip>
        </v-card-text>
      </v-card>
    </v-dialog>`,
  data: function () {
    return {
      dialog: false,
    };
  },
  computed: {
    title: function() {
      var title = [] 
      this.entry.meta.forEach(element => {
        if(element.name == "title"){
          if(!title.includes(element.value_str)){
            title.push(element.value_str);
          }
        }
      });
      title = title.join(', ')
      title = title.split(' ');
      return title
    },
    artist: function(){
      var artist = [] 
      this.entry.meta.forEach(element => {
        if(element.name == "artist_name"){
          artist.push(element.value_str)
        }
      });
      return artist.join(', ')
    },
    tags: function () {
      var tags = [];
      var count = 0
      for (let i = 0; i < this.entry.classifier.length; i++) {
        var classifier = this.entry.classifier[i];

        for (let j = 0; j < classifier.annotations.length; j++) {
          tags.push({
            id: count, disable: classifier.annotations[j].value < 0.6,
            name: capitalize(classifier.annotations[j].name),
          });
          count += 1;
        }
      }
      return tags;
    },
    date: function () {

      var year_min = null; 
      this.entry.meta.forEach(element => {
        if(element.name == "year_min"){
          year_min = element.value_str;
        }
      });

      var year_max = null; 
      this.entry.meta.forEach(element => {
        if(element.name == "year_max"){
          year_max =element.value_str;
        }
      });
      if (year_min && year_max) {
        if (year_min == year_max) return year_min;
        return year_min + "–" + year_max;
      }

      if (year_min) return year_min;
      if (year_max) return year_max;
    },
    annotations: function () {
      var TAGS_ALLOW = ['medium', 'perspective'];
      var tags = [];
      var tags_name = [];
      var count = 0

      this.entry.meta.forEach(element => {
        if(TAGS_ALLOW.includes(element.name)){
          if(!tags_name.includes(element.value_str)){
            tags.push({
              id: count,
              name: capitalize(element.value_str),
            });
            tags_name.push(element.value_str);
            count += 1;
          }
        }
      });
      console.log(tags);
      return tags;

    },
    entry: function () {
      return this.$store.state.selected;
    },
    isWide: function () {
      // TODO
      return false;
    },
    updateDialog: function () {
      return this.$store.state.dialog == "detail";
    },
  },
  methods: {
    searchArtist(value) {
      // TODO
      this.close();
    },
    close() {
      this.dialog = false;
    }
  },
  watch: {
    updateDialog: function (value) {
      if (value) {
        this.dialog = value;  // open dialog
        this.$store.commit("updateDialog", null);
      }
    },
  },
});

Vue.component("detail-view-menu", {
  template: `
    <v-menu offset-y bottom right>
      <template v-slot:activator="{ attrs, on: menu }">
        <v-fab-transition v-if="type=='image'">
          <v-btn 
            v-bind="attrs" v-on="menu" title="Search for similar objects" 
            color="primary" fab absolute bottom right large
          >
            <v-icon>mdi-image-search-outline</v-icon>
          </v-btn>
        </v-fab-transition>

        <v-btn 
          v-if="type=='meta'" class="search title--click" text 
          v-bind="attrs" v-on="menu" :title="item"
        >
          {{item}}
        </v-btn>

        <v-btn 
          v-if="type=='annotations'" class="search" text 
          v-bind="attrs" v-on="menu" 
        >
          <v-icon size="18" right>mdi-magnify</v-icon>
        </v-btn>
      </template>

      <v-list>
        <v-list-item>
          <v-btn text @click="search(false)">Launch new search</v-btn>
        </v-list-item>

        <v-list-item>
          <v-btn text @click="search(true)">Append to search</v-btn>
        </v-list-item>
      </v-list>
    </v-menu>`,
  props: ["item", "type"],
  methods: {
    search(add) {
      this.$store.commit("updateQuery", {
        name: this.item, group: this.type,
        add: add,  // add item to search bar
      });

      this.$store.commit("toggleSubmit");
      this.$emit("closeDialog");
    },
  },
});

Vue.component("search-bar", {
  template: `
    <v-container class="py-4 search-bar" align-content="center">
      <v-combobox
        v-model="search" :items="items" :search-input.sync="suggest"
        prepend-inner-icon="mdi-magnify" @click:prepend-inner="submit" 
        append-icon="mdi-image-search-outline" @click:append="searchImage"
        placeholder="Start typing to search" @keyup.enter="submit" rounded 
        item-text="name" item-value="id" clearable solo hide-no-data flat 
        multiple hide-selected menu-props=closeOnClick
      >
        <template v-slot:selection="{ attrs, select, selected, item, index }">
          <v-menu :content-class="item.group" :close-on-content-click="false">
            <template v-slot:activator="{ on }">
              <v-chip 
                v-on="on" v-bind="attrs" :input-value="selected" 
                @click:close="deleteItem(index)" close
              >
                <span v-if="item.group!=null">
                  <v-icon v-if="item.group=='meta'" size="18" left>mdi-information-outline</v-icon>
                  <v-icon v-if="item.group=='annotations'" size="18" left>mdi-tag-text-outline</v-icon>
                  <v-icon v-if="item.group=='image'" size="18" left>mdi-image-outline</v-icon>
                  
                  <span v-if="item.group!='image'" :title="item.name">{{item.name}}</span>
                  <span v-else :title="item.name.meta.title">{{item.name.meta.title}}</span>
                </span>
                <span v-else :title="item">{{item}}</span>
              </v-chip>
            </template>

            <v-card v-if="item.group=='image'" width="300">
              <v-img 
                :src="item.name.path" class="grey lighten-1" contain max-height="200"
              ></v-img>

              <v-card-text>
                <feature-selector-local :item.sync="item" :index="index" @update="updateWeights"/>
              </v-card-text>
            </v-card>
          </v-menu>
        </template>

        <template v-slot:item="{ on, item }">
          <v-list-item v-on="on">
            <v-list-item-icon class="my-2 mr-3">
              <v-icon v-if="item.group=='meta'" size=20>mdi-information-outline</v-icon>
              <v-icon v-if="item.group=='annotations'" size=20>mdi-tag-text-outline</v-icon>
            </v-list-item-icon>

            <v-list-item-content>
              <v-list-item-title>{{item.name}}</v-list-item-title>
            </v-list-item-content>
          </v-list-item>
        </template>
      </v-combobox>

      <search-image/>
    </v-container>`,
  data: function () {
    return {
      suggest: null,
      search: [],
      items: [],
    };
  },
  computed: {
    updateItems: function () {
      var state = this.$store.state.suggestions,
        entries = [];  // converted suggestions


      for (let i = 0; i < state.length; i++) {
        var values = state[i].suggestions,
          group = state[i].group;

        for (let j = 0; j < values.length; j++) {
          entries.push({
            id: entries.length, group: group,
            name: capitalize(values[j]),
          });
        }
      }

      return entries;
    },
    updateQuery: function () {
      return this.$store.state.query;
    },
    updateSubmit: function () {
      return this.$store.state.submit;
    },
  },
  methods: {
    submit() {
      var queries = [];

      for (let i = 0; i < this.search.length; i++) {
        if (typeof this.search[i] === "object") {
          if (this.search[i].group == "image") {
            if (
              "weights" in this.search[i] &&
              Object.keys(this.search[i].weights).length
            ) {
              queries.push({
                reference: this.search[i].name.id,
                features: this.search[i].weights,
              });
            } else {
              queries.push({
                reference: this.search[i].name.id,
                features: this.$store.state.weights,
              });
            }
          } else {
            queries.push({
              query: this.search[i].name,
              type: this.search[i].group,
            });
          }
        } else {
          queries.push({
            query: this.search[i], type: null,
          });
        }
      }

      this.$store.dispatch("search", {
        queries: queries,
        sorting: this.$store.state.sorting,
        mapping: this.$store.state.layout.mapping,
      });
    },
    deleteItem(index) {
      this.search.splice(index, 1);
    },
    updateWeights(index, weights) {
      this.search[index]["weights"] = weights;
    },
    searchImage() {
      this.$store.commit("updateDialog", "search");
    },
  },
  watch: {
    updateQuery: function (query) {
      for (let i = 0; i < this.search.length; i++) {
        if (this.search[i].group == query.group) {
          if (typeof this.search[i].name === typeof query.name) {
            if (this.search[i].name === query.name) {
              return;
            }

            if (typeof this.search[i].name === "object") {
              if (this.search[i].name.id == query.name.id) {
                return;
              }
            }
          }
        }
      }

      if ("add" in this.$store.state.query) {
        if (this.$store.state.query.add) {
          this.search.push(query); 
          return;
        }
      }

      this.search = [query];
    },
    updateItems: function (items) {
      this.items = items;
    },
    updateSubmit: function (value) {
      if (value) {
        this.submit();  // run updated query
        this.$store.commit("toggleSubmit");
      }
    },
    suggest: function (query) {
      if (query != null) {
        this.$store.dispatch("refreshAutocomplete", {
          query: query,  // get new suggestion
        });
      }
    },
  },
});

Vue.component("search-image", {
  template: `
    <v-dialog v-model="dialog" max-width="350px">
      <v-card>
        <v-card-title>
          Image search

          <v-btn icon @click="close" absolute right>
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-card-title>

        <v-card-text>
          <v-switch v-model="selectFile" class="pt-0" inset label="Upload image from my computer"></v-switch>
          <v-file-input 
            v-if="selectFile" v-model="file" :rules="[rules.isFile]" accept="image/png, image/jpeg, image/gif"
            placeholder="Select image file" prepend-icon="mdi-camera" chips show-size filled
          ></v-file-input>
          <v-text-field 
            v-else v-model="url" :rules="[rules.isUrl]" placeholder="Paste URL to image" 
            prepend-icon="mdi-link-variant" clearable filled
          ></v-text-field>
        </v-card-text>

        <v-card-actions class="px-6 pb-6">
          <v-btn @click="search" color="secondary" block rounded>Search</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>`,
  data: function () {
    return {
      file: null,
      url: null,
      dialog: false,
      selectFile: false,
      rules: {
        isFile(value) {
          if (!value || value.size < 2000000) {
            return true;
          }

          return "Image size should be less than 2 MB.";
        },
        isUrl(value) {
          var pattern = new RegExp(
            "(http|ftp|https)://[\w-]+(\.[\w-]+)+([\w.,@?^" +
            "=%&amp;:/~+#-]*[\w@?^=%&amp;/~+#-])?"
          );

          if (pattern.test(value)) {
            return true;
          }

          return "Requested URL is not valid.";
        },
      },
    };
  },
  computed: {
    updateDialog: function () {
      return this.$store.state.dialog == "search";
    },
  },
  methods: {
    close() {
      this.dialog = false;
    },
    search() {
      this.$store.dispatch("upload", {
        file: this.file, url: this.url
      });

      this.close();
    },
  },
  watch: {
    updateDialog: function (value) {
      if (value) {
        this.dialog = value;  // open dialog
        this.$store.commit("updateDialog", null);
      }
    },
  },
});

Vue.component("settings", {
  template: `
    <div>
      <v-btn icon @click="toggle">
        <v-icon>mdi-cog-outline</v-icon>
      </v-btn>

      <v-navigation-drawer v-model="drawer" width="300" app absolute right temporary hide-overlay>
        <v-toolbar flat class="v-bar--underline">
          <v-toolbar-title>Settings</v-toolbar-title>

          <v-btn icon @click="close" absolute right>
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-toolbar>

        <v-container>
          <layout-settings/>
          <div class="mt-4 mb-3 mx-n3"><v-divider/></div>
          <feature-selector-global/>
          <div class="mt-4 mb-3 mx-n3"><v-divider/></div>
          <search-settings/>
        </v-container>
      </v-navigation-drawer>
    </div>`,
  data: function () {
    return {
      drawer: false,
    };
  },
  methods: {
    toggle() {
      this.drawer = !this.drawer;
    },
    close() {
      this.drawer = false;
    },
  },
});

Vue.component("feature-selector-global", {
  template: `
    <div class="pl-1">
      <div class="mb-2 text-subtitle-1">Feature weights</div>

      <v-row class="mb-n2">
        <feature-slider 
          v-for="(weight, name, id) in weights" :key="id" :name="name" 
          :weight="weight" :sum="sumWeights" @updateWeight="updateWeight" 
          hide-details dense
        />
      </v-row>
    </div>`,
  data: function () {
    return {
      weights: this.$store.state.weights,
    };
  },
  computed: {
    sumWeights: function () {
      let sum = 0;

      for (let key in this.weights) {
        sum += this.weights[key];
      }

      return sum;
    },
  },
  methods: {
    updateWeight(plugin, value) {
      this.weights[plugin] = value;  // change single weight
      this.$store.commit("updateWeights", this.weights);
    },
  },
});

Vue.component("feature-selector-local", {
  template: `
    <div>
      <v-switch 
        v-model="local" class="pt-0" inset hide-details
        label="Specify local search weights"
      ></v-switch>

      <v-row v-if="local" class="mt-6 mb-n3">
        <feature-slider 
          v-for="(weight, name, id) in weights" :key="id" :name="name" 
          :weight="weight" :sum="sumWeights" @updateWeight="updateWeight" 
          hide-details dense
        />
      </v-row>
    </div>`,
  props: ["index", "item"],
  data: function () {
    return {
      local: false,
      weights: {},
    };
  },
  computed: {
    sumWeights: function () {
      let sum = 0;

      for (let key in this.weights) {
        sum += this.weights[key];
      }

      return sum;
    },
  },
  methods: {
    updateWeight(plugin, value) {
      this.weights[plugin] = value;
      this.updateWeights();
    },
    updateWeights() {
      if (this.local) {
        this.$emit("update", this.index, this.weights);
      } else {
        this.$emit("update", this.index, {});
      }
    },
  },
  created: function () {
    this.weights = { ...this.$store.state.weights };
  },
  watch: {
    local: function (value) {
      this.updateWeights();
    },
    item: function() {
      if ("weights" in this.item) {
        this.local = true;
        this.weights = this.item.weights;
      } else {
        this.local = false;
        this.weights = {...this.$store.state.weights};
      }
    }
  },
});

Vue.component("feature-slider", {
  template: `
    <v-col cols="12" class="pt-0" :title="title">
      <v-slider v-model="value" @change="process" :prepend-icon="icon">
        <template v-slot:append>
          <v-text-field v-model="value" class="mt-0 pt-0" type="number"></v-text-field>
        </template>
      </v-slider>
    </v-col>`,
  props: ["name", "weight", "sum"],
  data: function () {
    return {
      data: {
        yuv_histogram_feature: {
          icon: "mdi-palette",
          title: "Color Features",
        },
        byol_embedding_feature: {
          icon: "mdi-bank-outline",
          title: "Wikimedia Features",
        },
        image_net_inception_feature: {
          icon: "mdi-earth",
          title: "ImageNet Features"
        },
        clip_embedding_feature: {
          icon: "mdi-image-outline",
          title: "CLIP Features"
        },
      },
      value: this.weight * 100,
    };
  },
  computed: {
    icon: function () {
      return this.data[this.name].icon;
    },
    title: function () {
      return this.data[this.name].title;
    },
  },
  methods: {
    process() {
      // restrict value, if the other weights are set to 0
      if (this.sum - this.weight < 0.1) {
        this.value = 10;
      }

      this.$emit("updateWeight", this.name, this.value / 100);
    },
  },
});

Vue.component("layout-settings", {
  template: `
    <div class="pl-1">
      <div class="mb-2 text-subtitle-1">Layout</div>

      <v-item-group v-model="selected" mandatory>
        <v-row class="px-2">
          <v-col v-for="(item, id) in items" :key="id" @click="update" cols="12" md="6" class="pa-1">
            <v-item v-slot="{ active, toggle }">
              <v-card
                @click="toggle" :color="active ? 'primary' : 'grey lighten-3'"
                class="d-flex align-center py-3 px-4" height="60" :dark="active" flat
              >
                <span>{{item.text}}</span>
                <v-icon :dark="active" large>{{item.icon}}</v-icon>
              </v-card>
            </v-item>
          </v-col>
        </v-row>
      </v-item-group>

      <div v-if="mapping=='umap'">
        <div class="mt-4 mb-3 ml-n4 mr-n3"><v-divider/></div>
        <umap-settings/>
      </div>
    </div>`,
  data: function () {
    return {
      selected: 0,
      items: [
        {
          height: 200, width: "auto", text: "Flexible",
          icon: "mdi-view-compact-outline", mapping: null,
        },
        {
          height: 200, width: 200, text: "Regular",
          icon: "mdi-view-comfy-outline", mapping: null,
        },
        {
          height: 200, width: 200, text: "Canvas",
          icon: "mdi-vector-polyline", mapping: "umap",
        },
      ],
    };
  },
  computed: {
    mapping: function () {
      return this.items[this.selected].mapping;
    },
  },
  methods: {
    update: function () {
      let layout = {
        width: this.items[this.selected].width,
        height: this.items[this.selected].height,
        mapping: this.mapping,
      };

      if (this.$store.state.layout.mapping != layout.mapping) {
        // if mapping changes, trigger search again
        this.$store.commit("toggleSubmit");
        this.$store.commit("updateZoomLevel", 0);
      }

      this.$store.commit("updateLayout", layout);
    },
  },
})

Vue.component("umap-settings", {
  template: `
    <div>
      <div class="mb-2 text-subtitle-1">Image size</div>

      <v-col cols="12" class="pa-0">
        <v-slider 
          v-model="meshSize" prepend-icon="mdi-image-size-select-large"
          @change="process" step="0.1" min="1.0" max="5.0"
        >
          <template v-slot:append>
            <v-text-field v-model="meshSize" class="mt-0 pt-0" type="number"></v-text-field>
          </template>
        </v-slider>
      </v-col>
    </div>`,
  data: function () {
    return {
      meshSize: this.$store.state.meshSize,
    }
  },
  methods: {
    process: function () {
      this.$store.commit("updateMeshSize", this.meshSize);
    }
  },
})

Vue.component("search-settings", {
  template: `
    <div class="pl-1">
      <div class="mb-3 text-subtitle-1">Search results</div>

      <v-row class="mx-1">
        <v-switch 
          v-model="sorting" class="pt-0" inset hide-details
          label="Sort search results randomly" @change="update"
        ></v-switch>
      </v-row>
    </div>`,
  data: function () {
    return {
      sorting: false,
    };
  },
  methods: {
    update() {
      if (this.sorting) {
        this.$store.commit("updateSorting", "random");
      } else {
        this.$store.commit("updateSorting", null);
      }
    },
  },
});

Vue.component("user-menu", {
  template: `
    <v-menu offset-y bottom left :close-on-content-click="false">
      <template v-slot:activator="{ attrs, on: menu }">
        <v-btn icon v-bind="attrs" v-on="menu" class="mr-n3">
          <v-icon>mdi-account-details</v-icon>
        </v-btn>
      </template>

      <v-list>
        <v-list-item><user-login/></v-list-item>
        <v-list-item><user-register/></v-list-item>
      </v-list>
    </v-menu>`,
});

Vue.component("user-login", {
  template: `
    <v-dialog v-model="dialog" max-width="350px">
      <template v-slot:activator="{ attrs, on: dialog }">
        <v-btn text v-bind="attrs" v-on="dialog">
          Login
        </v-btn>
      </template>

      <v-card class="login">
        <v-card-title>
          Login

          <v-btn icon @click="close" absolute right>
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-card-title>

        <v-card-text>
          <v-text-field 
            placeholder="Username" prepend-icon="mdi-account" 
            clearable hide-details
          ></v-text-field>

          <v-text-field
            :append-icon="showPassword ? 'mdi-eye' : 'mdi-eye-off'"
            placeholder="Password" prepend-icon="mdi-lock" 
            @click:append="showPassword = !showPassword"
            :type="showPassword ? 'text' : 'password'"
            clearable hide-details
          ></v-text-field>
        </v-card-text>

        <v-card-actions class="px-6 pt-6">
          <v-btn @click="login" color="secondary" block rounded>Login</v-btn>
        </v-card-actions>

        <div class="grey--text px-6 pb-6 text--center">
          Don't have an account? <user-register @closeLogin="close"/>.
        </div>
      </v-card>
    </v-dialog>`,
  data: function () {
    return {
      dialog: false,
      showPassword: false,
    };
  },
  methods: {
    close() {
      this.dialog = false;
    },
    login() {
      // TODO
      this.close();
    }
  },
});

Vue.component("user-register", {
  template: `
    <v-dialog v-model="dialog" max-width="350px">
      <template v-slot:activator="{ attrs, on: dialog }">
        <v-btn text v-bind="attrs" v-on="dialog">
          Register
        </v-btn>
      </template>

      <v-card class="register">
        <v-card-title>
          Register

          <v-btn icon @click="close" absolute right>
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-card-title>

        <v-card-text>
          <v-text-field 
            placeholder="Username" prepend-icon="mdi-account" 
            clearable hide-details
          ></v-text-field>

          <v-text-field 
            placeholder="Email" prepend-icon="mdi-email" 
            clearable hide-details
          ></v-text-field>

          <v-text-field
            :append-icon="showPassword ? 'mdi-eye' : 'mdi-eye-off'"
            placeholder="Password" prepend-icon="mdi-lock" 
            @click:append="showPassword = !showPassword"
            :type="showPassword ? 'text' : 'password'"
            clearable hide-details
          ></v-text-field>
        </v-card-text>

        <v-card-actions class="pa-6">
          <v-btn @click="register" color="secondary" block rounded>Register</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>`,
  data: function () {
    return {
      dialog: false,
      showPassword: false,
    };
  },
  methods: {
    close() {
      this.dialog = false;
    },
    register() {
      // TODO
      this.close();
    },
  },
  watch: {
    dialog: function (value) {
      if (value) {
        this.$emit("closeLogin");
      }
    }
  },
});

Vue.component("progress-bar", {
  template: `
    <v-progress-linear 
      :style="loading? 'opacity: 1;' : 'opacity: 0'" 
      color="primary" absolute bottom indeterminate height="8"
    ></v-progress-linear>`,
  data: function () {
    return {
      loading: false,
    };
  },
  computed: {
    update: function () {
      return this.$store.state.search.status;
    },
  },
  watch: {
    update: function (value) {
      this.loading = value != null;
    }
  }
});

Vue.component("zoom-nav", {
  template: `
    <div class="zoom">
      <v-btn :disabled="!zoomInEnabled" color="primary" class="mr-1" @click="zoomIn" title="Zoom in" fab small>
        <v-icon>mdi-magnify-plus-outline</v-icon>
      </v-btn>

      <v-btn :disabled="!zoomOutEnabled" color="primary" @click="zoomOut" title="Zoom out" fab small>
        <v-icon>mdi-magnify-minus-outline</v-icon>
      </v-btn>
    </div>`,
  data: function () {
    return {
      zoomLevel: 0,
      zoomInEnabled: true,
      zoomOutEnabled: true,
    };
  },
  computed: {
    updateZoomLevel: function () {
      return this.$store.state.zoomLevel;
    },
  },
  methods: {
    zoomIn() {
      if (this.zoomLevel < 7) {
        this.zoomLevel += 1;
        this.commit();
      }
    },
    zoomOut() {
      if (this.zoomLevel > -7) {
        this.zoomLevel -= 1;
        this.commit();
      }
    },
    enableZoom() {
      this.zoomInEnabled = true;
      this.zoomOutEnabled = true;

      if (this.zoomLevel == 6) {
        this.zoomInEnabled = false;
      }

      if (this.zoomLevel == -6) {
        this.zoomOutEnabled = false;
      }
    },
    commit() {
      this.$store.commit("updateZoomLevel", this.zoomLevel);
    },
  },
  watch: {
    updateZoomLevel: function (value) {
      this.zoomLevel = value;
      this.enableZoom();
    }
  }
});

var app = new Vue({
  el: "#app",
  template: `
    <v-app>
      <v-app-bar class="v-bar--underline" app flat>
        <v-app-bar-nav-icon class="mr-4"></v-app-bar-nav-icon>
        <v-img src="url_static +'/img/logo.svg'" class="mr-4" max-height="40" max-width="100" contain></v-img>
        
        <search-bar/><settings/><user-menu/>
        <progress-bar/>
      </v-app-bar>

      <v-main 
      :style="loading? 'opacity: 0;' : 'opacity: 1'" >
        <umap v-if="mapping=='umap'"/>
        <gallery v-else/>

        <detail-view/>
      </v-main>

      <zoom-nav v-if="mapping!='umap'"/>
    </v-app>`,
  store,
  computed: {
    mapping: function () {
      return this.$store.state.layout.mapping;
    },
    loading: function () {
      return this.$store.state.search.status;
    },
  },
  mounted: function () {
    this.$store.commit("updateQuery", {
      name: "Landscape", group: "annotations",
    });
    this.$store.dispatch("listFeatures");
      

    this.$store.commit("toggleSubmit");
    this.$intro().start();
  },
  vuetify: new Vuetify({
    theme: {
      themes: {
        light: {
          primary: "#B71C1C",
          secondary: "#D32F2F",
          accent: "#880E4F",
        },
      },
      dark: false,
    },
  }),
});
