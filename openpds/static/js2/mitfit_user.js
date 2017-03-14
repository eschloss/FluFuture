window.AnswerListMap = Backbone.View.extend({
    el: "#answerListMapContainer",
    
    initialize: function (locationAnswerKey, activityAnswerKey, center, mapContainerId, timesContainerId, autoResize) {
        _.bindAll(this, "render", "renderPlaces");

        if (mapContainerId) {
            this.mapContainerId = mapContainerId;
            this.el = "#" + mapContainerId;
        } else {
            this.mapContainerId = "answerListMapContainer";
        }

        if (timesContainerId) {
            this.timesContainerId = timesContainerId;
            this.timesEl = "#" + timesContainerId;
        } else {
            this.timesContainerId = "answerListTimesContainer";
            this.timesEl = "#" + timesContainerId;
        }
        this.timesElement = $(this.timesEl);
//        this.timesElement.append("The times you are most active:<br/>");

        this.autoResize = autoResize;
        this.center = center;
        this.render();
        this.locationAnswerLists = new AnswerListCollection([],{ "key": locationAnswerKey });
        this.activityAnswerLists = new AnswerListCollection([],{ "key": activityAnswerKey });
        this.locationAnswerLists.bind("reset", this.renderPlaces);
        this.activityAnswerLists.bind("reset", this.renderPlaces);
        this.locationAnswerLists.fetch();
        this.activityAnswerLists.fetch();
	var heatmap;
    },
    
    render: function () {
	var myLatlng = new google.maps.LatLng(42.361794,-71.090804);
	var myOptions = {
	  zoom: 15,
	  center: myLatlng,
	  mapTypeId: google.maps.MapTypeId.ROADMAP,
	  disableDefaultUI: false,
	  scrollwheel: true,
	  draggable: true,
	  navigationControl: true,
	  mapTypeControl: false,
	  scaleControl: true,
	  disableDoubleClickZoom: false
	};
	this.map = new google.maps.Map(document.getElementById("answerListMapContainer"), myOptions);

	heatmap = new HeatmapOverlay(this.map, {"radius":15, "visible":true, "opacity":60});
   },

    renderPlaces: function () {
        var locationEntries = (this.locationAnswerLists && this.locationAnswerLists.length > 0)? this.locationAnswerLists.at(0).get("value"):[];
        var activityEntries = (this.activityAnswerLists && this.activityAnswerLists.length > 0)? this.activityAnswerLists.at(0).get("value"):[];
        var highActivityLocations = [];
        var highActivityTimes = [];

	var locationPoints = [];
	var max = 0;
        for (i in locationEntries){
            var locationEntry = locationEntries[i];
            var centroid = locationEntry["centroid"];

            var startTime = locationEntry["start"];
            var endTime = locationEntry["end"];

            if(activityEntries[i] != undefined && centroid[0] != undefined){
                var high = activityEntries[i]["high"];
                var low = activityEntries[i]["low"];
		var total = activityEntries[i]["total"];
                if ( high + low > 0 ){
                    var normalizedActivity = Math.round((high + low)*500/(total)); //500 for testing. Need to look at various datasets to figure out formula.
		    if(max < normalizedActivity){
			max = normalizedActivity;
		    }
                    if (normalizedActivity > 1){
                        repeatLocation = false;
                        for (highActivityLocation in highActivityLocations){
                            if (centroid[0][0] == highActivityLocation[0] && centroid[0][1] == highActivityLocation[1]){
                                repeatLocation = true;
                                break;
                            }
                        }
                        if(repeatLocation == false){
                            highActivityLocations.push(centroid[0]);
			    locationPoints.push({lat: centroid[0][0], lng: centroid[0][1], count: normalizedActivity});
                        }

                        var startDate = new Date(startTime*1000);
                        var startHours = startDate.getHours();
                        var endDate = new Date(endTime*1000);
                        var endHours = endDate.getHours();

                        repeatTime = false;

                        for (highActivityTime in highActivityTimes){
                            if (startHours == highActivityTimes[highActivityTime]["start"] && endHours == highActivityTimes[highActivityTime]["end"]){
                                repeatTime = true;
                                break;
                            }
                        }

                        if(repeatTime == false){
                            this.timesElement.append("From " + this.formatTime(startHours) + " to " + this.formatTime(endHours) + "<br/>");
			    var time = {"start": startHours, "end": endHours};
			    highActivityTimes.push(time);
                        }
                    }
                }
            }
        }
	

	var testData = {
		max: max,
		data: locationPoints
	};

        // this is important, because if you set the data set too early, the latlng/pixel projection doesn't work
        google.maps.event.addListenerOnce(this.map, "idle", function(){
                heatmap.setDataSet(testData);
        });

    },

    formatTime: function (time) {
	var timeString = "";
        if(time == 12){
     	    timeString = "Noon";
        } else if (time == 24){
	    timeString = "Midnight";
        } else if(time > 12 && time < 24){
	    timeValue = time - 12;
	    timeString = timeValue + " PM";
        } else {
	    timeString = time + " AM";
        }
	return timeString;
    },

});
