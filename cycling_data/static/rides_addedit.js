function parseDate(fieldNum) {
    datestr=$("input[id='deformField"+fieldNum+"-date']").val()
    timestr=$("input[id='deformField"+fieldNum+"-time']").val()
    if(timestr=="") throw "Invalid time";
    datetimestr=(datestr + " " + timestr);
    return new Date(datetimestr);
}

function formatDate(date) {
    year=String(date.getFullYear())
    mon=String(date.getMonth()+1).padStart(2,'0')
    day=String(date.getDate()).padStart(2,'0')
    hour=String(date.getHours()).padStart(2,'0')
    minute=String(date.getMinutes()).padStart(2,'0')
    second=String(date.getSeconds()).padStart(2,'0')
    return year+'-'+mon+'-'+day+' '+hour+':'+minute+':'+second
}

function seconds_to_time_string(t){
    h=Math.floor(t/3600)
    m=Math.floor((t/3600-h)*60)
    s=t%60
    return [h,m,s].map(function(val){
	tokens=val.toString().split('.');
	tokens[0]=tokens[0].padStart(2,'0')
	return tokens.join('.')
    }).join(':')
}

$(document).ready(function() {

    var suffixes=['d','h','m','s'];

    ['rolling_time','total_time'].forEach(function(name){
	$('input[name='+name+']').next().find('input').each(
	    function (index,value){
		this.name=name+'_'+suffixes[index];
		this.id=name+'_'+suffixes[index];
	    }
	);
    });

    jQuery.validator.addMethod('end_time_after_start_time',function(value,element){
	try{
	    start_time=parseDate('3')
	    end_time=parseDate('4')
	}
	catch(err){
	    return true;
	}	

	if(start_time<end_time) return true;
	else return false;

    },'End time should be after start time')

    jQuery.validator.addMethod('check_total_time_consistent',function(value,element){
	try{
	    start_time=parseDate('3')
	    end_time=parseDate('4')
	}
	catch(err){
	    return true;
	}	

	interval_s=(end_time-start_time)/1000

	total_time_s=parseInt($("input[name='total_time']").val())
	if(isNaN(total_time_s) || isNaN(interval_s) || total_time_s == 0 ) return true;

	delta=Math.abs(interval_s-total_time_s)

	tol=60

	if(delta<tol) return true
	else return false

    },function(params,element){
	start_time=parseDate('3')
	end_time=parseDate('4')
	interval_s=(end_time-start_time)/1000
	return jQuery.validator.format(
	    'Expected total time is between {0} and {1}',
	    seconds_to_time_string(interval_s-tol),
	    seconds_to_time_string(interval_s+tol)
	)
    })
    
    jQuery.validator.addMethod('check_total_time_gte_rolling_time',function(value,element){
	try{
	    total_time_s=parseInt($("input[name='total_time']").val())
	    rolling_time_s=parseInt($("input[name='rolling_time']").val())
	}
	catch(err){
	    return true
	}
	if(isNaN(total_time_s) || isNaN(rolling_time_s) || total_time_s == 0 || rolling_time_s == 0) return true;

	if(rolling_time_s<total_time_s) return true;
	else return false;

    },'Total time should be greater than rolling time')
    
    jQuery.validator.addMethod('avspeed_consistent',function(value,element){
	try{
	    avspeed=parseFloat($("input[name='avspeed']").val())
	}
	catch(TypeError){
	    return true;
	}
	try{
	    distance=parseFloat($("input[name='distance']").val())
	}
	catch(TypeError){
	    return true;
	}
	try{
	    hours=parseInt($("input[name='rolling_time']").val())/3600.0
	}
	catch(err){
	    return true;
	}

	if(isNaN(avspeed) || isNaN(distance)) return true

	calcspeed=distance/hours
	ratio=avspeed/calcspeed
	if(ratio<0.99 || ratio>1.02) return false;
	else return true;
    },function(params,element){
	distance=parseFloat($("input[name='distance']").val())
	hours=parseInt($("input[name='rolling_time']").val())/3600.0
	calcspeed=distance/hours
	min=calcspeed*0.99
	max=calcspeed*1.02
	return jQuery.validator.format(
	    'Average speed should be between '+min.toFixed(2).toString()+' and '+max.toFixed(2).toString())
    });
    
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

	if(isNaN(maxspeed)) return true;
	if(isNaN(avspeed)) return true;
	
	if(maxspeed>avspeed) return true;
	else return false;
    },'Max speed should be greater than average speed.');
    
    $('[step]').each(function() {
	$(this).change(function(){
	    $(this).rules('remove', 'step');
	});
	$(this).blur(function(){
	    $(this).rules('remove', 'step');
	});
	$(this).focus(function(){
	    $(this).rules('remove', 'step');
	});
    });

  // Initialize form validation on the registration form.
  // It has the name attribute "registration"
    $("form[id='deform']").validate({
	onsubmit:false,
	rules:{
	    date:{
		end_time_after_start_time:true,
		check_total_time_consistent:true
	    },
	    time:{
		end_time_after_start_time:true,
		check_total_time_consistent:true
	    },
	    total_time_s:{
		check_total_time_consistent:true,
		check_total_time_gte_rolling_time:true
	    },
	    distance:{
		min:0,
		number:true,
		remote:{
		    url:'/rides/validation/distance',
		    type:'post',
		    data:{
			distance:function(){
			    return $("input[name='distance']").val()
			},
			odometer:function(){
			    return $("input[name='odometer']").val()
			},
			equipment_id:function(){
			    return $("select[name='equipment'] option:selected").val()
			},
			ride_id:function(){
			    return $("input[name='id']").val()
			},
			start_time:function(){
			    return formatDate(parseDate('3'))
			}
		    }
		},
		avspeed_consistent:true
	    },
	    rolling_time_s:{
		avspeed_consistent:true,
		check_total_time_gte_rolling_time:true
	    },
	    odometer:{
		min:0,
		number:true,
		remote:{
		    url:'/rides/validation/odometer',
		    type:'post',
		    data:{
			distance:function(){
			    return $("input[name='distance']").val()
			},
			odometer:function(){
			    return $("input[name='odometer']").val()
			},
			equipment_id:function(){
			    return $("select[name='equipment'] option:selected").val()
			},
			ride_id:function(){
			    return $("input[name='id']").val()
			},
			start_time:function(){
			    return formatDate(parseDate('3'))
			}
		    }
		},
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
	    },
	    rolling_time:{
		avspeed_consistent:true,
		check_total_time_gte_rolling_time:true
	    }
	},
    });
});
