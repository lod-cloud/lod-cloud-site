var app = new Vue({
    el: '#app',
    data: data(),
    methods: {
        commaFormatted: function (x) {
            return x.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
        },
        stars: function (dataset) {
            if (dataset.title) {
                if (dataset.description) {
                    if (dataset.contact_point) {
                        if (dataset.triples && dataset.triples > 0) {
                            if (dataset.links && dataset.links.length > 0) {
                                var accessible = false;
                                if (dataset.full_download) {
                                    for (i in dataset.full_download) {
                                        var download = dataset.full_download[i];
                                        if (typeof download.status === undefined || download.status === "OK") {
                                            accessible = true
                                        }
                                    }
                                }
                                if (dataset.other_download) {
                                    for (i in dataset.other_download) {
                                        var download = dataset.other_download[i];
                                        if (typeof download.status === undefined || download.status === "OK") {
                                            accessible = true
                                        }
                                    }
                                }

                                if (accessible) {
                                    var lwd = false;

                                    for (i in  dataset.sparql) {
                                        var download = dataset.sparql[i];
                                        if (download.status === "OK") {
                                            lwd = true;
                                        }
                                    }

                                    for (i in dataset.example) {
                                        var example = dataset.example[i];
                                        if (example.status === "OK" &&
                                                ["application/rdf+xml", "text/turtle", "application/n-triples", "appliation/ld+json"].includes(example.media_type)) {
                                            lwd = true;
                                        }
                                    }
                                    if (lwd) {
                                        return [5, "Linked Web Data"];
                                    } else {
                                        return [4, "No examples resolve to RDF"];
                                    }
                                } else {
                                    return [3, "Downloads may not be available"];
                                }
                            } else {
                                return [2, "No links to other datasets"];
                            }
                        } else {
                            return [2, "No triple count"];
                        }
                    } else {
                        return [1, "No contact point"];
                    }
                } else {
                    return [1, "No Description"];
                }
            } else {
                return [1, "No Title"];
            }
        },
        star_img: function (dataset) {
            var r = this.stars(dataset);

            return "/img/" + r[0] + "stars.png";
        },
        star_explain: function (dataset) {
            var r = this.stars(dataset);

            return r[1];
        },
        sort_links: function (links) {
            links.sort(function(t) {
                return t.target;
            });
            return links;
        } 
    },
    beforeMount() {
        if(resource2luzzu[this.dataset._id] != undefined) {
          this.dataset.show_luzzu = true;
          visualisationChart(resource2luzzu[this.dataset._id]);
        }
    }

})
