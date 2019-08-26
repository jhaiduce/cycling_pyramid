function parseDate(datestr) {
    var [datestr,timestr]=datestr.split(" ")
    var [y,mon,d]=datestr.split("-").map(parseFloat)
    var [h,min,s]=timestr.split(":").map(parseFloat)
    return new Date(y,mon-1,d,h,min,s)
}

$(function() {

    jQuery.validator.addMethod('end_time_after_start_time',function(value,element){
	start_time=parseDate($("input[name='start_time']").val())
	end_time=parseDate($("input[name='end_time']").val())

	if(start_time<end_time) return true;
	else return false;

    },'End time should be after start time')

    jQuery.validator.addMethod('check_total_time_consistent',function(value,element){
	start_time=parseDate($("input[name='start_time']").val())
	end_time=parseDate($("input[name='end_time']").val())

	interval_s=(end_time-start_time)/1000

	var [h,m,s]=$("input[name='total_time']").val().split(':').map(parseFloat)
	total_time_s=(h*3600+m*60+s)

	delta=Math.abs(interval_s-total_time_s)

	if(delta<60) return true;
	else return false;

    },'Total time is inconsistent with start and end times')
    
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
    
    jQuery.validator.addMethod('checkMaxspeedGteAvspeed',function(value,element){
	try{
	    avspeed=parseFloat($("input[name='avspeed']").val())
	}
	catch(TypeError){
	    return true;
	}
	try{
	    maxspeed=parseFloat($("input[name='maxspeed']").val())
	}
	catch(TypeError){
	    return true;
	}
	if(maxspeed>avspeed) return true;
	else return false;
    },'Max speed should be greater than average speed.');
    
    jQuery.validator.addMethod('checkOdometerDistance',function(value,element){
	try{
	    distance=parseFloat($("input[name='distance']").val())
	}
	catch(TypeError){
	    return true;
	}
	try{
	    odometer=parseFloat($("input[name='odometer']").val())
	}
	catch(TypeError){
	    return true;
	}
	equipment_id=parseInt($("select[name='equipment'] option:selected").val())
	start_time=$("input[name='start_time']").val()

	$.ajax({
	    url:'/rides/last_odo?equipment_id='+equipment_id+'&start_time='+start_time,
	    async:false,
	    dataType: 'json',
	    success:function(result){
		odometer_last=result.odometer
	    }});
	if(Math.abs(odometer_last+distance-odometer)>0.1){
	    return false;
	}
	else return true;
    },'Odometer value and ride distance do not match');

  // Initialize form validation on the registration form.
  // It has the name attribute "registration"
    $("form[id='deform']").validate({
	onsubmit:false,
	rules:{
	    start_time:{
		end_time_after_start_time:true,
		check_total_time_consistent:true
	    },
	    end_time:{
		end_time_after_start_time:true,
		check_total_time_consistent:true
	    },
	    total_time:{
		check_total_time_consistent:true
	    },
	    distance:{
		min:0,
		number:true,
		checkOdometerDistance:true
	    },
	    odometer:{
		min:0,
		number:true,
		checkOdometerDistance:true
	    },
	    maxspeed:{
		min:0,
		number:true,
		checkMaxspeedGteAvspeed:true
	    },
	    avspeed:{
		min:0,
		number:true,
		avspeed_consistent:true,
		checkMaxspeedGteAvspeed:true
	    }
	},
    });
});
