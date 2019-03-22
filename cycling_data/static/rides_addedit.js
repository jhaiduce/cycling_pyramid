$(function() {
  // Initialize form validation on the registration form.
  // It has the name attribute "registration"
    $("form[id='deform']").validate({
	rules:{
	    distance:{
		min:0,
		number:true
	    },
	    odometer:{
		min:0,
		number:true
	    },
	    maxspeed:{
		min:0,
		number:true
	    },
	    avspeed:{
		min:0,
		number:true
	    }
	},
    });
});
