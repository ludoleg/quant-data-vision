var List = Vue.extend({
    template: '#mode-list',
    delimiters: ['[[',']]'],
    data: function () {
        return {
            modes: [],
            searchKey: ''
        };
    },
    created: function() {
        axios.post('/mode')
            .then((response) => {
                console.log(response);
                this.modes = response.data;
                console.log(this.modes);
            })
            .catch(function (error) {
                if (error.response) {
                    // The request was made and the server responded with a status code
                    // that falls out of the range of 2xx
                    console.log(error.response.data);
                    console.log(error.response.status);
                    console.log(error.response.headers);
                } else if (error.request) {
                    // The request was made but no response was received
                    // `error.request` is an instance of XMLHttpRequest in the browser and an instance of
                    // http.ClientRequest in node.js
                    console.log(error.request);
                } else {
                    // Something happened in setting up the request that triggered an Error
                    console.log('Error', error.message);
                }
                console.log(error.config);
            });
    },
    computed : {
        filteredModes: function () {
            var self = this;
            console.log();
            return self.modes.filter(function (mode) {
                return mode.title.indexOf(self.searchKey) !== -1;
            });
        }
    }
});

var Mode = Vue.extend({
    delimiters: ['[[',']]'],
    template: '#mode',
    data: function () {
        return {
            mode: ''
        };
    },
    mounted: function () {
        var mode = this.mode;
        axios.get('/modes/edit', {
            params: {
                mode_id: this.$route.params.mode_id }
        })
            .then((response) => {
                console.log(response);
                this.mode = response.data;
                console.log(this.modes);
            })
            .catch(function (error) {
                console.log(error);
            });
    }
});


var ModeEdit = Vue.extend({
    delimiters: ['[[',']]'],
    template: '#mode-edit',
    data: function () {
        return {
            form: {
                title: this.$route.params.title,
                lambda: this.$route.params.lambda,
                target: this.$route.params.target,
                fwhma: this.$route.params.fwhma,
                fwhmb: this.$route.params.fwhmb,
                inventory: this.$route.params.inventory,
                oldinventory: this.$route.params.inventory,
                mode_id: this.$route.params.id
            },
            options: {
                target: [
                    { value: 'Cu', text: "Cu"},
                    { value: 'Co', text: "Co"}
                ],
                inventory: [ { value: 'rockforming', text: "Rock Forming"},
                             { value: 'pigment', text: "Pigment"},
                             { value: 'cement', text: "Cement"},
                             { value: 'chemin', text: "Chemin"}]
            }
        };
    },
    methods: {
        updateMode: function () {
            var mode = this.mode;
            axios.post('/modes/edit', this.form )
                .then(function (response) {
                    console.log(response);
                })
                .catch(function (error) {
                    console.log(error);
                });
            router.push('/');
        }
    }
});

var ModeDelete = Vue.extend({
    delimiters: ['[[',']]'],
    template: '#mode-delete',
    data: function () {
        return {
            mode: {
                title: this.$route.params.mode_title,
                mode_id: this.$route.params.mode_id
            }
        };
    },
    methods: {
        deleteMode: function () {
            var mode = this.mode;
            console.log(this.mode);
            axios.post('/modes', this.mode )
                .then(function (response) {
                    console.log(response);
                })
                .catch(function (error) {
                    console.log(error);
                });
            router.push('/');
        }
    }
});
var AddMode = Vue.extend({
    template: '#add-mode',
    delimiters: ['[[',']]'],
    data: function () {
        return {
            form: {
                title: '',
                lambda: parseFloat(0),
                target: 'Cu',
                fwhma: parseFloat(0),
                fwhmb: 0.3,
                inventory: 'rockforming'
            },
            options: {
                target: [
                    { value: 'Cu', text: "Cu"},
                    { value: 'Co', text: "Co"}
                ],
                inventory: [ { value: 'rockforming', text: "Rock Forming"},
                             { value: 'pigment', text: "Pigment"},
                             { value: 'cement', text: "Cement"},
                             { value: 'chemin', text: "Chemin"}]
            }
        };
    },
    methods: {
        createMode: function() {
            var form = this.form;
            console.log(this.form);
            axios.post('/modes/create', this.form )
                .then(function (response) {
                    console.log(response);
                })
                .catch(function (error) {
                    console.log(error);
                });
            router.push('/');
        }
    }
});

var router = new VueRouter({
    routes: [
        {path: '/', component: List},
        {path: '/mode/:mode_id', component: Mode, name: 'mode'},
        {path: '/add-mode', component: AddMode},
        {path: '/mode/edit/:title', component: ModeEdit, props: true, name: 'mode-edit' },
        {path: '/mode/:mode_id/delete', component: ModeDelete, name: 'mode-delete'}
    ]});

new Vue({
    el: '#app',
    delimiters: ['[[',']]'],
    router: router,
    template: '<router-view></router-view>'
});
