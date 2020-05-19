var app = new Vue({
    el: '#app',
    data: data(),
    created: function () {
        //this.domains = ['cross-domain', 'geography', 'government', 'life_sciences', 'linguistics', 'media', 'publications', 'social_networking', 'user_generated'],
        //this.route.paramMap
        //       .switchMap((params:ParamMap) => this.datasetService.getDataset(params.get('id')))
        //	.subscribe(td => {this.dataset = td.dataset[0]; this.contactPoint = this.dataset.contact_point;});
        //this.datasetService.getDatasets()
        //	.then(td => {this.forLinks = td.datasets.map(a => a._id).sort(); }  );
    },
    props: ['apiMessage'],
    methods: {
        EditDataset: function (dataset) {

            if (!dataset) {
                return;
            }

            /*
             var datasetId = this.dataset._id;
             dataset.id = this.dataset._id;	*/

            if (dataset.keywords) {
                if (typeof dataset.keywords === "string") {
                    dataset.keywords = dataset.keywords.split(",");
                } else {
                    dataset.keywords = dataset.keywords.map(function (k) {
                        if (typeof k === "object") {
                            return k.text;
                        } else {
                            return k;
                        }
                    });
                }
            }

            this.$http.put("/api/" + dataset.identifier, dataset).then(function (response) {

                // get body data
                // redirect to 
                // 		"'/edit-dataset/' + dataset._id" 
                window.location.href = '/dataset/' + dataset.identifier;

            }, function (response) {
                alert(response.data);
                // error callback
                //window.history.back();
            });
            return false;
        },
        guidGenerator: function () {
            var S4 = function () {
                return (((1 + Math.random()) * 0x10000) | 0).toString(16).substring(1);
            };
            return (S4() + S4() + "-" + S4() + "-" + S4() + "-" + S4() + "-" + S4() + S4() + S4());
        },
        goBack: function () {
            this.location.back();
        },
        keywordHandle: function(dataset) {
            dataset.keywords = document.getElementById("keywords").value.split(",");
        },
        addKeyword: function (event) {
            var input = event.input;
            var value = event.value;

            if ((value || '').trim()) {
                this.dataset.keywords.push(value.trim());
            }

            if (input) {
                input.value = '';
            }
        },
        removeKeyword: function (fruit) {
            var index = this.dataset.keywords.indexOf(fruit);

            if (index >= 0) {
                this.dataset.keywords.splice(index, 1);
            }
        },
        //Dataset links
        addLink: function () {
            this.dataset.links.push({_id: this.guidGenerator(), target: "", value: ""});
        },
        deleteLink: function (idToRemove) {
            this.dataset.links.splice(idToRemove,1);
        },
        //Dataset example
        addExample: function () {
            this.dataset.example.push({_id: this.guidGenerator(), title: "", description: "", access_url: ""});
        },
        deleteExample: function (idToRemove) {
            this.dataset.example.splice(idToRemove,1);
        },
        //Dataset sparql
        addSparql: function () {
            this.dataset.sparql.push({_id: this.guidGenerator(), title: "", description: "", access_url: ""});
        },
        deleteSparql: function (idToRemove) {
            this.dataset.sparql.splice(idToRemove,1);
        },
        //Dataset full_download
        addFull_download: function () {
            this.dataset.full_download.push({_id: this.guidGenerator(), title: "", description: "", access_url: "", media_type: ""});
        },
        deleteFull_download: function (idToRemove) {
            this.dataset.full_download.splice(idToRemove,1);
        },
        //Dataset other_download
        addOther_download: function () {
            this.dataset.other_download.push({_id: this.guidGenerator(), title: "", description: "", access_url: "", media_type: ""});
        },
        deleteOther_download: function (idToRemove) {
            this.dataset.other_download.splice(idToRemove,1);
        }
    }
});


