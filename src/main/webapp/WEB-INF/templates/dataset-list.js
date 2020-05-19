var app = new Vue({
    el: '#app',
    data: data(),
    created: function () {
		this.datasets = this.datasets.sort((a,b) => (a._id > b._id) ? 1 : ((b._id > a._id) ? -1 : 0));
        this.datasetsNarrowed = this.datasets;
        this.setPage(1);

        // get current page of items
        this.datasetsToShow = this.datasetsNarrowed.slice(this.pager.startIndex, this.pager.endIndex + 1);
    },
    methods: {
        getPager: function (totalItems, currentPage) {
            var pageSize = 10;
            // calculate total pages
            var totalPages = Math.ceil(totalItems / pageSize);

            var startPage, endPage;
            if (totalPages <= 10) {
                // less than 10 total pages so show all
                startPage = 1;
                endPage = totalPages;
            } else {
                // more than 10 total pages so calculate start and end pages
                if (currentPage <= 6) {
                    startPage = 1;
                    endPage = 10;
                } else if (currentPage + 4 >= totalPages) {
                    startPage = totalPages - 9;
                    endPage = totalPages;
                } else {
                    startPage = currentPage - 5;
                    endPage = currentPage + 4;
                }
            }

            // calculate start and end item indexes
            var startIndex = (currentPage - 1) * pageSize;
            var endIndex = Math.min(startIndex + pageSize - 1, totalItems - 1);

            // create an array of pages to ng-repeat in the pager control
            //var pages = _.range(startPage, endPage + 1);
            var pages = []
            for(i = startPage; i < endPage + 1; i++) {
                pages.push(i);
            }

            // return object with all pager properties required by the view
            return {
                totalItems: totalItems,
                currentPage: currentPage,
                pageSize: pageSize,
                totalPages: totalPages,
                startPage: startPage,
                endPage: endPage,
                startIndex: startIndex,
                endIndex: endIndex,
                pages: pages
            };
        },
        setPage: function (page) {
            // get pager object from service
            this.pager = this.getPager(this.datasetsNarrowed.length, page);

            if(this.pager.totalPages == 0) {
                this.datasetsToShow = [];
            }
            // check page isn't out of range
            if (page < 1 || page > this.pager.totalPages) {
                return;
            }
            // get current page of items
            this.datasetsToShow = this.datasetsNarrowed.slice(this.pager.startIndex, this.pager.endIndex + 1);
        },
        onSearchChange: function (query) {
            this.lastQuery = query;
            filteredDatasets = this.datasets.filter(function (t) {
                return(t._id.includes(query) || t.title.includes(query)/* || (t.description && t.description.en && t.description.en.includes(query))*/ );
            }).sort();
            ////this.apiMessage = td.message;
            this.datasetsNarrowed = filteredDatasets;
            this.setPage(1);
        },
		 /** Debounce search input by 100 ms */
		onSearchInput () {
		  clearTimeout(this.searchDebounce)
		  this.searchDebounce = setTimeout(async () => {
			this.searchOffset = 0
			this.searchResults = await this.search()
		  }, 100)
		},
		/** Call API to search for inputted term */
		async search () {
		  console.log(`${window.location.pathname}?search=`+this.searchQuery);
		  window.location.href = `${window.location.pathname}?search=`+this.searchQuery;
		},
		
        AddDataset: function (dataset) {
            if (!dataset) {
                return;
            }
            this.datasetService.createDataset(dataset)
                    .then(function (td) {
                        console.log(td);
                        this.datasets.push(td.dataset);
                        //update search
                        this.onSearchChange(this.lastQuery);
                    });
        },
        showDeleteDataset: function (dataset) {
            this.datasetToDelete = dataset;
            this.apiMessage = "";
        },
        deleteDataset: function (dataset) {
            if (!dataset) {
                return;
            }
            var datasetId = dataset._id;
            this.datasetService.deleteDataset(dataset)
                    .then(function (td) {
                        filteredDatasets = this.datasets.filter(function (t) {
                            t._id !== datasetId
                        });
                        //const filteredDatasetsToShow = this.datasetsToShow.filter(t => t._id !== datasetId);				
                        this.apiMessage = td.message;
                        this.datasets = filteredDatasets;
                        //this.datasetsToShow = filteredDatasetsToShow;	

                        //update search
                        this.onSearchChange(this.lastQuery);
                    });
        }
    }
});

