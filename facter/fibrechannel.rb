Facter.add(:fibrechannel) do
  confine :kernel => 'Linux'
  confine :virtual => 'physical'
  setcode do
    host_data = Facter::Core::Execution.execute('systool -c fc_host -v')
    host_data.gsub!("\n\"\n", "\"\n")
    res = {:hosts => {}}
    device_name, fc_host = nil, nil
    for line in host_data.split("\n")
      if line.strip == '' then
        res[:hosts][device_name] = fc_host if fc_host
        fc_host = nil
      elsif /^\s+(?<key>[^=]+)\s+=\s+"(?<val>[^"]+)"$/ =~ line then
        key.strip!
        if fc_host.nil? then
          if key == "Class Device" then
            device_name, fc_host = val, {}
          end
        elsif key == "Class Device path" then
          # ignore
        else
          val.strip!
          val = val.split(', ') if key =~ /^supported_/
          val = val.split(' ')[0] if key =~ /_type$/
          val = val.sub('0x', '') if key =~ /(_name|port_id)$/
          fc_host[key] = val
        end
      end
    end
    res
  end
end

