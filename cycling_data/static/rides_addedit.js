$(function() {

    jQuery.validator.addMethod('avspeed_consistent',function(value,element){
	try{
	    distance=parseFloat($("input[name='distance']").val())
	}
	catch(TypeError){
	    return true;
	}
	try{
	    t=$("input[name='rolling_time']").val().split(':').map(parseFloat)
	}
	catch(TypeError){
	    return true;
	}
	hours=t[0]+t[1]/60.0+t[2]/3600.0
	calcspeed=distance/hours
	ratio=value/calcspeed
	if(ratio<0.99 || ratio>1.02) return false;
	else return true;
    },'Average speed is inconsistent with the time and distance entered');
    
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
		number:true,
		avspeed_consistent:true
	    }
	},
    });
});
